package io.github.aigen.article.domain;

import java.util.ArrayList;
import java.util.List;

/**
 * Input command / value object for article generation requests.
 *
 * <p>Only {@code category} is mandatory. All other fields are optional and fall back to the
 * values configured in {@code ArticleGeneratorProperties}.
 *
 * <p>Example usage:
 * <pre>{@code
 * ArticleRequest request = ArticleRequest.builder()
 *     .category("Spring Boot")
 *     .subcategory("Spring Security")
 *     .tag("JWT Authentication")
 *     .language("en")
 *     .avoidTitles(List.of("Introduction to JWT", "JWT basics"))
 *     .build();
 * }</pre>
 */
public class ArticleRequest {

    /** Category (parent) — required. */
    private String category;

    /** Sub-category — defaults to {@code "General"}. */
    private String subcategory = "General";

    /** Topic / tag for the article — optional. */
    private String tag;

    /**
     * Explicit title to use for the article.
     * When set the AI generates the body around this exact title instead of creating a new one.
     */
    private String title;

    /**
     * Author username — overrides {@code article-generator.author-username} for this request.
     * If {@code null} the property value is used.
     */
    private String authorUsername;

    /**
     * Site base URL for canonical links — overrides {@code article-generator.site} for this
     * request. If {@code null} the property value is used.
     */
    private String site;

    /**
     * ISO 639-1 language code — overrides {@code article-generator.language} for this request.
     * If {@code null} the property value is used.
     */
    private String language;

    /**
     * Titles to avoid (deduplication). The AI is instructed not to produce a title that is
     * too similar (≥ similarity threshold) to any entry in this list.
     */
    private List<String> avoidTitles = new ArrayList<>();

    // ── Constructors ──────────────────────────────────────────────────────

    public ArticleRequest() {}

    private ArticleRequest(Builder builder) {
        this.category = builder.category;
        this.subcategory = builder.subcategory;
        this.tag = builder.tag;
        this.title = builder.title;
        this.authorUsername = builder.authorUsername;
        this.site = builder.site;
        this.language = builder.language;
        this.avoidTitles = builder.avoidTitles;
    }

    // ── Builder ───────────────────────────────────────────────────────────

    public static Builder builder() {
        return new Builder();
    }

    public static final class Builder {
        private String category;
        private String subcategory = "General";
        private String tag;
        private String title;
        private String authorUsername;
        private String site;
        private String language;
        private List<String> avoidTitles = new ArrayList<>();

        public Builder category(String category) {
            this.category = category;
            return this;
        }

        public Builder subcategory(String subcategory) {
            this.subcategory = subcategory;
            return this;
        }

        public Builder tag(String tag) {
            this.tag = tag;
            return this;
        }

        public Builder title(String title) {
            this.title = title;
            return this;
        }

        public Builder authorUsername(String authorUsername) {
            this.authorUsername = authorUsername;
            return this;
        }

        public Builder site(String site) {
            this.site = site;
            return this;
        }

        public Builder language(String language) {
            this.language = language;
            return this;
        }

        public Builder avoidTitles(List<String> avoidTitles) {
            this.avoidTitles = avoidTitles != null ? new ArrayList<>(avoidTitles) : new ArrayList<>();
            return this;
        }

        public ArticleRequest build() {
            if (category == null || category.isBlank()) {
                throw new IllegalArgumentException("ArticleRequest.category is required");
            }
            return new ArticleRequest(this);
        }
    }

    // ── Getters & Setters ─────────────────────────────────────────────────

    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }

    public String getSubcategory() { return subcategory; }
    public void setSubcategory(String subcategory) { this.subcategory = subcategory; }

    public String getTag() { return tag; }
    public void setTag(String tag) { this.tag = tag; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getAuthorUsername() { return authorUsername; }
    public void setAuthorUsername(String authorUsername) { this.authorUsername = authorUsername; }

    public String getSite() { return site; }
    public void setSite(String site) { this.site = site; }

    public String getLanguage() { return language; }
    public void setLanguage(String language) { this.language = language; }

    public List<String> getAvoidTitles() { return avoidTitles; }
    public void setAvoidTitles(List<String> avoidTitles) {
        this.avoidTitles = avoidTitles != null ? avoidTitles : new ArrayList<>();
    }

    @Override
    public String toString() {
        return "ArticleRequest{category='" + category + "', subcategory='" + subcategory
                + "', tag='" + tag + "', language='" + language + "'}";
    }
}
