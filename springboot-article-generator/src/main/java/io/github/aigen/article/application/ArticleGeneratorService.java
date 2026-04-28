package io.github.aigen.article.application;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.aigen.article.domain.Article;
import io.github.aigen.article.domain.ArticleRequest;
import io.github.aigen.article.port.in.ArticleGeneratorPort;
import io.github.aigen.article.port.out.ArticleRepositoryPort;
import io.github.aigen.shared.ai.port.AiPort;
import io.github.aigen.shared.config.ArticleGeneratorProperties;
import io.github.aigen.shared.util.JsonUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

/**
 * Application service that implements the {@link ArticleGeneratorPort} use case.
 *
 * <p>This class orchestrates AI-powered article generation with full SEO metadata.
 * It depends on the {@link AiPort} output port (fulfilled by {@link AiClientAdapter}) and
 * internal application helpers ({@link PromptBuilderService}, {@link SeoService},
 * {@link TextUtils}).
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
public class ArticleGeneratorService implements ArticleGeneratorPort {

    private static final Logger log = LoggerFactory.getLogger(ArticleGeneratorService.class);

    private final ArticleGeneratorProperties properties;
    private final AiPort aiPort;
    private final PromptBuilderService promptBuilder;
    private final TextUtils textUtils;
    private final JsonUtils jsonUtils;
    private final ArticleAssembler assembler;
    private final ArticleRepositoryPort repository;

    public ArticleGeneratorService(
            ArticleGeneratorProperties properties,
            AiPort aiPort,
            PromptBuilderService promptBuilder,
            TextUtils textUtils,
            JsonUtils jsonUtils,
            ArticleAssembler assembler,
            ArticleRepositoryPort repository) {
        this.properties   = properties;
        this.aiPort       = aiPort;
        this.promptBuilder = promptBuilder;
        this.textUtils    = textUtils;
        this.jsonUtils    = jsonUtils;
        this.assembler    = assembler;
        this.repository   = repository;
    }

    // ── ArticleGeneratorPort implementation ───────────────────────────────

    /**
     * {@inheritDoc}
     */
    @Override
    public Article generateArticle(ArticleRequest request) {
        validateRequest(request);

        String category    = request.getCategory();
        String subcategory = request.getSubcategory() != null ? request.getSubcategory() : "General";
        String tag         = request.getTag();
        String language    = request.getLanguage()       != null ? request.getLanguage()       : properties.getLanguage();
        String site        = request.getSite()           != null ? request.getSite()           : properties.getSite();
        String author      = request.getAuthorUsername() != null ? request.getAuthorUsername() : properties.getAuthorUsername();
        List<String> avoidTitles = new ArrayList<>(request.getAvoidTitles());

        log.info("Generating article: category='{}', subcategory='{}', tag='{}', language='{}'",
                category, subcategory, tag, language);

        String title, summary, body;
        List<String> keywords;

        if (request.getTitle() != null && !request.getTitle().isBlank()) {
            var result = generateArticleContent(category, subcategory, tag,
                    request.getTitle(), avoidTitles, language);
            title    = request.getTitle();
            summary  = result.summary();
            body     = textUtils.replaceH1(result.body(), title);
            keywords = result.keywords();
        } else {
            var phase1 = generateArticleContent(category, subcategory, tag,
                    null, avoidTitles, language);

            if (!textUtils.isTooSimilar(phase1.title(), avoidTitles, properties.getSimilarityThreshold())) {
                title    = phase1.title();
                summary  = phase1.summary();
                body     = phase1.body();
                keywords = phase1.keywords();
            } else {
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

        Article article = assembler.assemble(title, summary, body, keywords,
                category, subcategory, tag, author, site, language);
        log.info("Article generated: title='{}', slug='{}', words={}, readingTime={}min",
                article.getTitle(), article.getSlug(),
                article.getWordCount(), article.getReadingTime());
        return repository.save(article);
    }

    // ── Content generation helpers ────────────────────────────────────────

    private ArticleContent generateArticleContent(
            String category, String subcategory, String tag,
            String title, List<String> avoidTitles, String language) {

        String prompt = promptBuilder.buildGenerationPrompt(
                category, subcategory, tag, title, avoidTitles, language);

        String rawText = aiPort.generate(
                promptBuilder.getGenerationSystemMsg(),
                prompt,
                properties.getMaxArticleTokens(),
                properties.getTemperatureArticle());

        String jsonBlock = jsonUtils.extractJsonBlock(rawText);
        JsonNode data    = jsonUtils.safeJsonParse(jsonBlock);

        String parsedTitle   = textNode(data, "title");
        String parsedSummary = textNode(data, "summary");
        String parsedBody    = textNode(data, "body");
        List<String> kw      = keywordList(data);

        if (parsedTitle.isBlank() || parsedBody.isBlank()) {
            throw new RuntimeException(
                    "AI response is missing required fields 'title' and/or 'body'. "
                    + "Raw JSON preview: " + jsonBlock.substring(0, Math.min(300, jsonBlock.length())));
        }

        if (!parsedBody.toLowerCase().contains("<h1")) {
            parsedBody = "<h1>" + textUtils.htmlEscape(parsedTitle) + "</h1>\n" + parsedBody;
        }

        return new ArticleContent(parsedTitle, parsedSummary, parsedBody, kw);
    }

    private String generateTitleOnly(String category, String subcategory, String tag,
                                      List<String> avoidTitles, String language) {
        String prompt = promptBuilder.buildTitlePrompt(
                category, subcategory, tag, avoidTitles, language);

        String rawText = aiPort.generate(
                promptBuilder.getTitleSystemMsg(),
                prompt,
                properties.getMaxTitleTokens(),
                properties.getTemperatureTitle());

        return rawText.strip()
                .replaceAll("^[\"']|[\"']$", "")
                .strip();
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

    // ── Inner types ───────────────────────────────────────────────────────

    private record ArticleContent(String title, String summary, String body, List<String> keywords) {}
}
