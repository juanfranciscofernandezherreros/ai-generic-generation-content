package com.github.juanfernandez.article.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.github.juanfernandez.article.config.ArticleGeneratorProperties;
import com.github.juanfernandez.article.model.Article;
import com.github.juanfernandez.article.model.ArticleRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Main service for AI-powered article generation with full SEO metadata.
 *
 * <h2>Generation algorithm (two-phase deduplication)</h2>
 *
 * <p><strong>Phase 1 — full generation</strong>: Calls the AI with the complete prompt to obtain
 * title, summary, HTML body and keywords.  If the generated title is not too similar to any
 * entry in {@code avoidTitles} (threshold {@link ArticleGeneratorProperties#getSimilarityThreshold()})
 * the article is accepted and Phase 2 is skipped.
 *
 * <p><strong>Phase 2 — title-only regeneration</strong>: When the Phase 1 title is a duplicate,
 * the HTML body is reused and only the title is regenerated (up to
 * {@link ArticleGeneratorProperties#getMaxTitleRetries()} times).  The {@code <h1>} in the body is
 * updated with the accepted title.
 *
 * <p>Transient network errors are retried with exponential back-off
 * ({@link ArticleGeneratorProperties#getMaxApiRetries()} retries,
 * {@link ArticleGeneratorProperties#getRetryBaseDelaySeconds()} seconds base delay).
 */
public class ArticleGeneratorService {

    private static final Logger log = LoggerFactory.getLogger(ArticleGeneratorService.class);
    private static final Random RANDOM = new Random();

    private final ArticleGeneratorProperties properties;
    private final AiClientService aiClient;
    private final PromptBuilderService promptBuilder;
    private final SeoService seoService;
    private final TextUtils textUtils;

    public ArticleGeneratorService(
            ArticleGeneratorProperties properties,
            AiClientService aiClient,
            PromptBuilderService promptBuilder,
            SeoService seoService,
            TextUtils textUtils) {
        this.properties = properties;
        this.aiClient = aiClient;
        this.promptBuilder = promptBuilder;
        this.seoService = seoService;
        this.textUtils = textUtils;
    }

    // ── Public API ────────────────────────────────────────────────────────

    /**
     * Generates a complete SEO article from an {@link ArticleRequest}.
     *
     * <p>Per-request fields ({@code authorUsername}, {@code site}, {@code language}) override the
     * corresponding values from {@link ArticleGeneratorProperties} when non-null.
     *
     * @param request article generation parameters
     * @return fully populated {@link Article} with SEO metadata
     * @throws IllegalArgumentException if {@code request.category} is blank
     * @throws RuntimeException         if the AI fails to generate a unique title after all retries
     */
    public Article generateArticle(ArticleRequest request) {
        validateRequest(request);

        String category    = request.getCategory();
        String subcategory = request.getSubcategory() != null ? request.getSubcategory() : "General";
        String tag         = request.getTag();
        String language    = request.getLanguage()      != null ? request.getLanguage()      : properties.getLanguage();
        String site        = request.getSite()          != null ? request.getSite()          : properties.getSite();
        String author      = request.getAuthorUsername()!= null ? request.getAuthorUsername(): properties.getAuthorUsername();
        List<String> avoidTitles = new ArrayList<>(request.getAvoidTitles());

        log.info("Generating article: category='{}', subcategory='{}', tag='{}', language='{}'",
                category, subcategory, tag, language);

        String title, summary, body;
        List<String> keywords;

        if (request.getTitle() != null && !request.getTitle().isBlank()) {
            // ── Explicit title mode ──────────────────────────────────────────
            var result = generateArticleContent(category, subcategory, tag,
                    request.getTitle(), avoidTitles, language);
            title    = request.getTitle();
            summary  = result.summary();
            body     = textUtils.replaceH1(result.body(), title);
            keywords = result.keywords();
        } else {
            // ── Auto-title mode with deduplication ───────────────────────────
            var phase1 = generateArticleContent(category, subcategory, tag,
                    null, avoidTitles, language);

            if (!textUtils.isTooSimilar(phase1.title(), avoidTitles, properties.getSimilarityThreshold())) {
                title    = phase1.title();
                summary  = phase1.summary();
                body     = phase1.body();
                keywords = phase1.keywords();
            } else {
                // Phase 2: body is valid, regenerate only the title
                log.warn("Phase 1 title '{}' is too similar to existing titles — starting title regeneration.",
                        phase1.title());
                avoidTitles.add(phase1.title());
                summary  = phase1.summary();
                body     = phase1.body();
                keywords = phase1.keywords();
                title    = null;

                int maxRetries = properties.getMaxTitleRetries();
                for (int attempt = 2; attempt <= maxRetries; attempt++) {
                    String newTitle = generateTitleOnly(category, subcategory, tag, avoidTitles, language);
                    if (!textUtils.isTooSimilar(newTitle, avoidTitles, properties.getSimilarityThreshold())) {
                        title = newTitle;
                        body  = textUtils.replaceH1(body, newTitle);
                        break;
                    }
                    log.warn("Attempt {}/{}: title '{}' is still too similar — retrying.",
                            attempt, maxRetries, newTitle);
                    avoidTitles.add(newTitle);
                }

                if (title == null) {
                    throw new RuntimeException(
                            "Could not generate a unique title after " + maxRetries + " attempts. "
                            + "Consider increasing article-generator.max-title-retries or adjusting "
                            + "article-generator.similarity-threshold.");
                }
            }
        }

        // ── Assemble the article with SEO metadata ────────────────────────
        return assembleArticle(title, summary, body, keywords, category, subcategory, tag,
                author, site, language);
    }

    // ── Content generation helpers ────────────────────────────────────────

    private ArticleContent generateArticleContent(
            String category, String subcategory, String tag,
            String title, List<String> avoidTitles, String language) {

        String prompt = promptBuilder.buildGenerationPrompt(
                category, subcategory, tag, title, avoidTitles, language);

        String rawText = withRetry(() -> aiClient.generate(
                promptBuilder.getGenerationSystemMsg(),
                prompt,
                properties.getMaxArticleTokens(),
                properties.getTemperatureArticle()));

        String jsonBlock = aiClient.extractJsonBlock(rawText);
        JsonNode data    = aiClient.safeJsonParse(jsonBlock);

        String parsedTitle   = textNode(data, "title");
        String parsedSummary = textNode(data, "summary");
        String parsedBody    = textNode(data, "body");
        List<String> kw      = keywordList(data);

        if (parsedTitle.isBlank() || parsedBody.isBlank()) {
            throw new RuntimeException(
                    "AI response is missing required fields 'title' and/or 'body'. "
                    + "Raw JSON preview: " + jsonBlock.substring(0, Math.min(300, jsonBlock.length())));
        }

        // Ensure body has an <h1>
        if (!parsedBody.toLowerCase().contains("<h1")) {
            parsedBody = "<h1>" + textUtils.htmlEscape(parsedTitle) + "</h1>\n" + parsedBody;
        }

        return new ArticleContent(parsedTitle, parsedSummary, parsedBody, kw);
    }

    private String generateTitleOnly(String category, String subcategory, String tag,
                                      List<String> avoidTitles, String language) {
        String prompt = promptBuilder.buildTitlePrompt(
                category, subcategory, tag, avoidTitles, language);

        String rawText = withRetry(() -> aiClient.generate(
                promptBuilder.getTitleSystemMsg(),
                prompt,
                properties.getMaxTitleTokens(),
                properties.getTemperatureTitle()));

        return rawText.strip()
                .replaceAll("^[\"']|[\"']$", "")  // strip wrapping quotes if any
                .strip();
    }

    // ── Article assembly ──────────────────────────────────────────────────

    private Article assembleArticle(
            String title, String summary, String body, List<String> keywords,
            String category, String subcategory, String tag,
            String author, String site, String language) {

        String nowIso = Instant.now().toString();
        String slug = textUtils.slugify(title);
        int wordCount   = textUtils.countWords(body);
        int readingTime = textUtils.estimateReadingTime(body);

        String metaTitle = truncate(title,   properties.getMetaTitleMaxLength());
        String metaDesc  = truncate(summary, properties.getMetaDescriptionMaxLength());
        String canonical = seoService.buildCanonicalUrl(site, slug);

        List<String> tagNames = (tag != null && !tag.isBlank()) ? List.of(tag) : List.of();

        Map<String, Object> structuredData = seoService.buildJsonLdStructuredData(
                title, summary, canonical, keywords,
                author, nowIso, nowIso,
                wordCount, readingTime,
                subcategory, tagNames, site, language);

        Article article = new Article();
        article.setTitle(title);
        article.setSlug(slug);
        article.setSummary(summary);
        article.setBody(body);
        article.setCategory(subcategory);
        article.setTags(tagNames);
        article.setAuthor(author);
        article.setStatus("published");
        article.setVisible(true);
        article.setKeywords(keywords);
        article.setMetaTitle(metaTitle);
        article.setMetaDescription(metaDesc);
        article.setCanonicalUrl(canonical);
        article.setStructuredData(structuredData);
        article.setOgTitle(metaTitle);
        article.setOgDescription(metaDesc);
        article.setOgType("article");
        article.setWordCount(wordCount);
        article.setReadingTime(readingTime);
        article.setPublishDate(nowIso);
        article.setCreatedAt(nowIso);
        article.setUpdatedAt(nowIso);
        article.setGeneratedAt(nowIso);

        log.info("Article generated: title='{}', slug='{}', words={}, readingTime={}min",
                title, slug, wordCount, readingTime);

        return article;
    }

    // ── Retry with exponential back-off ───────────────────────────────────

    /**
     * Executes {@code fn} with exponential back-off retries for transient network errors.
     *
     * <p>Only retries on {@link java.net.ConnectException}, {@link java.net.SocketTimeoutException}
     * and similar I/O errors.  Business exceptions (e.g. invalid API key) are re-thrown immediately.
     */
    private <T> T withRetry(ThrowingSupplier<T> fn) {
        int maxRetries = properties.getMaxApiRetries();
        int baseDelay  = properties.getRetryBaseDelaySeconds();
        Exception lastException = null;

        for (int attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return fn.get();
            } catch (RuntimeException e) {
                // Retry only on network-level errors
                if (isTransientError(e)) {
                    lastException = e;
                    double wait = baseDelay * Math.pow(2, attempt - 1) + RANDOM.nextDouble();
                    log.warn("Transient error on attempt {}/{}: {}. Retrying in {}s.",
                            attempt, maxRetries, e.getMessage(), String.format("%.1f", wait));
                    try { Thread.sleep((long) (wait * 1000)); } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        throw new RuntimeException("Interrupted during retry wait", ie);
                    }
                } else {
                    throw e;
                }
            } catch (Exception e) {
                throw new RuntimeException("Unexpected error calling AI API", e);
            }
        }
        throw new RuntimeException("AI API failed after " + maxRetries + " retries", lastException);
    }

    private boolean isTransientError(RuntimeException e) {
        Throwable cause = e.getCause() != null ? e.getCause() : e;
        String msg = cause.getClass().getName() + " " + (cause.getMessage() != null ? cause.getMessage() : "");
        return msg.contains("ConnectException")
                || msg.contains("SocketTimeoutException")
                || msg.contains("ConnectionRefused")
                || msg.contains("UnknownHostException");
    }

    // ── Utility ───────────────────────────────────────────────────────────

    private void validateRequest(ArticleRequest request) {
        if (request == null) throw new IllegalArgumentException("ArticleRequest must not be null");
        if (request.getCategory() == null || request.getCategory().isBlank()) {
            throw new IllegalArgumentException("ArticleRequest.category is required");
        }
    }

    private static String textNode(JsonNode node, String field) {
        JsonNode n = node.path(field);
        return n.isMissingNode() || n.isNull() ? "" : n.asText("").strip();
    }

    private static List<String> keywordList(JsonNode node) {
        JsonNode kw = node.path("keywords");
        if (!kw.isArray()) return List.of();
        List<String> list = new ArrayList<>();
        kw.forEach(k -> {
            String s = k.asText("").strip();
            if (!s.isBlank()) list.add(s);
        });
        return list;
    }

    private static String truncate(String s, int maxLen) {
        if (s == null) return "";
        return s.length() > maxLen ? s.substring(0, maxLen).stripTrailing() : s;
    }

    // ── Inner types ───────────────────────────────────────────────────────

    private record ArticleContent(String title, String summary, String body, List<String> keywords) {}

    @FunctionalInterface
    private interface ThrowingSupplier<T> {
        T get() throws Exception;
    }
}
