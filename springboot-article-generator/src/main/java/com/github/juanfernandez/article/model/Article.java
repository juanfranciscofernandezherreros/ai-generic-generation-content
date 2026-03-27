package com.github.juanfernandez.article.model;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.List;
import java.util.Map;

/**
 * Generated article with full SEO metadata.
 *
 * <p>All fields are serialized to JSON by Jackson ({@code @JsonInclude(NON_NULL)}) and can be
 * consumed directly by REST clients or stored in a document database.
 *
 * <p>The {@code structuredData} field contains Schema.org {@code TechArticle} JSON-LD data
 * that can be inlined in a {@code <script type="application/ld+json">} tag.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Article {

    // ── Core content ──────────────────────────────────────────────────────

    /** Article title (SEO-optimised, ≤ 60 characters recommended). */
    private String title;

    /** URL-safe slug derived from the title. */
    private String slug;

    /** SEO meta-description (≤ 160 characters recommended). */
    private String summary;

    /** Full article body as semantic HTML. */
    private String body;

    // ── Taxonomy ─────────────────────────────────────────────────────────

    /** Sub-category name (articleSection). */
    private String category;

    /** Tag / topic names. */
    private List<String> tags;

    // ── Authorship & status ───────────────────────────────────────────────

    /** Author username. */
    private String author;

    /** Publication status — always {@code "published"} for generated articles. */
    private String status = "published";

    /** Whether the article is publicly visible. */
    private boolean isVisible = true;

    // ── Keywords ─────────────────────────────────────────────────────────

    /** SEO long-tail keywords extracted by the AI. */
    private List<String> keywords;

    // ── SEO metadata ─────────────────────────────────────────────────────

    /** Truncated title for {@code <title>} tag (≤ metaTitleMaxLength characters). */
    private String metaTitle;

    /** Truncated summary for meta-description (≤ metaDescriptionMaxLength characters). */
    private String metaDescription;

    /** Canonical URL: {@code {site}/post/{slug}}. */
    private String canonicalUrl;

    /** Schema.org TechArticle JSON-LD structured data. */
    private Map<String, Object> structuredData;

    // ── Open Graph ────────────────────────────────────────────────────────

    /** Open Graph title. */
    private String ogTitle;

    /** Open Graph description. */
    private String ogDescription;

    /** Open Graph type — always {@code "article"}. */
    private String ogType = "article";

    // ── Statistics ────────────────────────────────────────────────────────

    /** Approximate word count of the article body. */
    private int wordCount;

    /** Estimated reading time in minutes. */
    private int readingTime;

    // ── Timestamps ────────────────────────────────────────────────────────

    /** ISO 8601 publish date (UTC). */
    private String publishDate;

    /** ISO 8601 creation timestamp (UTC). */
    private String createdAt;

    /** ISO 8601 last-modified timestamp (UTC). */
    private String updatedAt;

    /** ISO 8601 generation timestamp (UTC). */
    private String generatedAt;

    // ── Constructors ──────────────────────────────────────────────────────

    public Article() {}

    // ── Getters & Setters ─────────────────────────────────────────────────

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getSlug() { return slug; }
    public void setSlug(String slug) { this.slug = slug; }

    public String getSummary() { return summary; }
    public void setSummary(String summary) { this.summary = summary; }

    public String getBody() { return body; }
    public void setBody(String body) { this.body = body; }

    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }

    public List<String> getTags() { return tags; }
    public void setTags(List<String> tags) { this.tags = tags; }

    public String getAuthor() { return author; }
    public void setAuthor(String author) { this.author = author; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public boolean isVisible() { return isVisible; }
    public void setVisible(boolean visible) { isVisible = visible; }

    public List<String> getKeywords() { return keywords; }
    public void setKeywords(List<String> keywords) { this.keywords = keywords; }

    public String getMetaTitle() { return metaTitle; }
    public void setMetaTitle(String metaTitle) { this.metaTitle = metaTitle; }

    public String getMetaDescription() { return metaDescription; }
    public void setMetaDescription(String metaDescription) { this.metaDescription = metaDescription; }

    public String getCanonicalUrl() { return canonicalUrl; }
    public void setCanonicalUrl(String canonicalUrl) { this.canonicalUrl = canonicalUrl; }

    public Map<String, Object> getStructuredData() { return structuredData; }
    public void setStructuredData(Map<String, Object> structuredData) { this.structuredData = structuredData; }

    public String getOgTitle() { return ogTitle; }
    public void setOgTitle(String ogTitle) { this.ogTitle = ogTitle; }

    public String getOgDescription() { return ogDescription; }
    public void setOgDescription(String ogDescription) { this.ogDescription = ogDescription; }

    public String getOgType() { return ogType; }
    public void setOgType(String ogType) { this.ogType = ogType; }

    public int getWordCount() { return wordCount; }
    public void setWordCount(int wordCount) { this.wordCount = wordCount; }

    public int getReadingTime() { return readingTime; }
    public void setReadingTime(int readingTime) { this.readingTime = readingTime; }

    public String getPublishDate() { return publishDate; }
    public void setPublishDate(String publishDate) { this.publishDate = publishDate; }

    public String getCreatedAt() { return createdAt; }
    public void setCreatedAt(String createdAt) { this.createdAt = createdAt; }

    public String getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(String updatedAt) { this.updatedAt = updatedAt; }

    public String getGeneratedAt() { return generatedAt; }
    public void setGeneratedAt(String generatedAt) { this.generatedAt = generatedAt; }

    @Override
    public String toString() {
        return "Article{title='" + title + "', slug='" + slug + "', wordCount=" + wordCount
                + ", readingTime=" + readingTime + "min}";
    }
}
