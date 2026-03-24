package com.github.juanfernandez.article.service;

import com.github.juanfernandez.article.config.ArticleGeneratorProperties;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * SEO utilities: canonical URL builder and Schema.org JSON-LD structured data generator.
 *
 * <p>Mirrors the Python {@code seo.py} module.
 */
public class SeoService {

    private final ArticleGeneratorProperties properties;

    public SeoService(ArticleGeneratorProperties properties) {
        this.properties = properties;
    }

    /**
     * Builds the canonical URL for an article: {@code {site}/post/{slug}}.
     *
     * @param site base site URL (e.g. {@code https://myblog.com}); may be empty
     * @param slug URL-safe article slug
     * @return canonical URL, or empty string when either parameter is blank
     */
    public String buildCanonicalUrl(String site, String slug) {
        if (site == null || site.isBlank() || slug == null || slug.isBlank()) return "";
        return site.stripTrailing().replaceAll("/+$", "") + "/post/" + slug;
    }

    /**
     * Generates a Schema.org {@code TechArticle} JSON-LD document for the article.
     *
     * <p>The returned map can be serialised to JSON and embedded in a
     * {@code <script type="application/ld+json">} tag.
     *
     * @param title         article title
     * @param summary       article summary / meta-description
     * @param canonicalUrl  canonical URL of the article
     * @param keywords      SEO keywords
     * @param authorName    author username or full name
     * @param datePublished ISO 8601 publish date
     * @param dateModified  ISO 8601 last-modified date
     * @param wordCount     article word count
     * @param readingTime   estimated reading time in minutes
     * @param categoryName  sub-category name (used as {@code articleSection})
     * @param tagNames      tag names (used as {@code about} entities)
     * @param site          base site URL (used for {@code publisher})
     * @param language      ISO 639-1 language code
     * @return structured data map ready for JSON serialisation
     */
    public Map<String, Object> buildJsonLdStructuredData(
            String title,
            String summary,
            String canonicalUrl,
            List<String> keywords,
            String authorName,
            String datePublished,
            String dateModified,
            int wordCount,
            int readingTime,
            String categoryName,
            List<String> tagNames,
            String site,
            String language) {

        String baseUrl = (site != null) ? site.replaceAll("/+$", "") : "";

        Map<String, Object> author = new HashMap<>();
        author.put("@type", "Person");
        author.put("name", authorName != null ? authorName : "");

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("@context", "https://schema.org");
        data.put("@type", "TechArticle");
        data.put("headline", title != null ? (title.length() > 110 ? title.substring(0, 110) : title) : "");
        data.put("description", summary != null ? (summary.length() > 200 ? summary.substring(0, 200) : summary) : "");
        data.put("author", author);
        data.put("datePublished", datePublished != null ? datePublished : "");
        data.put("dateModified", dateModified != null ? dateModified : "");
        data.put("wordCount", wordCount);
        data.put("timeRequired", "PT" + readingTime + "M");
        data.put("inLanguage", language != null ? language : "es");
        data.put("keywords", keywords != null ? String.join(", ", keywords) : "");
        data.put("articleSection", categoryName != null ? categoryName : "");

        if (canonicalUrl != null && !canonicalUrl.isBlank()) {
            data.put("url", canonicalUrl);
            Map<String, Object> mainEntity = new HashMap<>();
            mainEntity.put("@type", "WebPage");
            mainEntity.put("@id", canonicalUrl);
            data.put("mainEntityOfPage", mainEntity);
        }

        if (!baseUrl.isBlank()) {
            String publisherName = baseUrl.replace("https://", "").replace("http://", "");
            Map<String, Object> publisher = new HashMap<>();
            publisher.put("@type", "Organization");
            publisher.put("name", publisherName);
            publisher.put("url", baseUrl);
            data.put("publisher", publisher);
        }

        if (tagNames != null && !tagNames.isEmpty()) {
            List<Map<String, Object>> about = new ArrayList<>();
            for (String tag : tagNames) {
                Map<String, Object> thing = new HashMap<>();
                thing.put("@type", "Thing");
                thing.put("name", tag);
                about.add(thing);
            }
            data.put("about", about);
        }

        return data;
    }
}
