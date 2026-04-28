package com.github.juanfernandez.article.article.application;

import com.github.juanfernandez.article.article.domain.Article;
import com.github.juanfernandez.article.shared.config.ArticleGeneratorProperties;

import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * Application collaborator that assembles a fully-populated {@link Article} from raw
 * AI-generated content and request context.
 *
 * <p>Splits SEO-metadata / structured-data / timestamp duties out of
 * {@link ArticleGeneratorService}, which now focuses solely on AI orchestration and the
 * deduplication loop.
 */
public class ArticleAssembler {

    private final ArticleGeneratorProperties properties;
    private final SeoService seoService;
    private final TextUtils textUtils;

    public ArticleAssembler(ArticleGeneratorProperties properties,
                            SeoService seoService,
                            TextUtils textUtils) {
        this.properties = properties;
        this.seoService = seoService;
        this.textUtils = textUtils;
    }

    /**
     * Builds a complete {@link Article} from the AI-generated text and the surrounding
     * request context.
     *
     * @param title       AI-generated (or user-supplied) title
     * @param summary     AI-generated summary / meta-description
     * @param body        full HTML body
     * @param keywords    SEO keywords extracted by the AI
     * @param category    parent category (informative; not stored)
     * @param subcategory sub-category — stored as {@code articleSection}
     * @param tag         optional tag/topic
     * @param author      author username
     * @param site        base site URL (used to build the canonical URL)
     * @param language    ISO 639-1 language code
     * @return fully-populated immutable-ish {@link Article}
     */
    public Article assemble(String title,
                             String summary,
                             String body,
                             List<String> keywords,
                             String category,
                             String subcategory,
                             String tag,
                             String author,
                             String site,
                             String language) {

        String nowIso      = Instant.now().toString();
        String slug        = textUtils.slugify(title);
        int    wordCount   = textUtils.countWords(body);
        int    readingTime = textUtils.estimateReadingTime(body);

        String metaTitle = truncate(title,   properties.getMetaTitleMaxLength());
        String metaDesc  = truncate(summary, properties.getMetaDescriptionMaxLength());
        String canonical = seoService.buildCanonicalUrl(site, slug);

        List<String> tagNames = (tag != null && !tag.isBlank()) ? List.of(tag) : List.of();

        Map<String, Object> structuredData = seoService.buildJsonLdStructuredData(
                title, summary, canonical, keywords,
                author, nowIso, nowIso,
                wordCount, readingTime,
                subcategory, tagNames, site, language);

        return Article.builder()
                .title(title)
                .slug(slug)
                .summary(summary)
                .body(body)
                .category(subcategory)
                .tags(tagNames)
                .author(author)
                .status("published")
                .visible(true)
                .keywords(keywords)
                .metaTitle(metaTitle)
                .metaDescription(metaDesc)
                .canonicalUrl(canonical)
                .structuredData(structuredData)
                .ogTitle(metaTitle)
                .ogDescription(metaDesc)
                .ogType("article")
                .wordCount(wordCount)
                .readingTime(readingTime)
                .publishDate(nowIso)
                .createdAt(nowIso)
                .updatedAt(nowIso)
                .generatedAt(nowIso)
                .build();
    }

    private static String truncate(String s, int maxLen) {
        if (s == null) return "";
        return s.length() > maxLen ? s.substring(0, maxLen).stripTrailing() : s;
    }
}
