package io.github.aigen.article.application;

import io.github.aigen.shared.config.ArticleGeneratorProperties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link SeoService}.
 */
class SeoServiceTest {

    private SeoService seoService;

    @BeforeEach
    void setUp() {
        ArticleGeneratorProperties props = new ArticleGeneratorProperties();
        props.setSite("https://myblog.com");
        props.setLanguage("es");
        seoService = new SeoService(props);
    }

    // ── buildCanonicalUrl ─────────────────────────────────────────────────

    @Test
    void buildCanonicalUrl_formatsCorrectly() {
        assertEquals("https://myblog.com/post/my-slug",
                seoService.buildCanonicalUrl("https://myblog.com", "my-slug"));
    }

    @Test
    void buildCanonicalUrl_stripsTrailingSlash() {
        assertEquals("https://myblog.com/post/my-slug",
                seoService.buildCanonicalUrl("https://myblog.com/", "my-slug"));
    }

    @Test
    void buildCanonicalUrl_returnsEmptyWhenSiteBlank() {
        assertEquals("", seoService.buildCanonicalUrl("", "my-slug"));
        assertEquals("", seoService.buildCanonicalUrl(null, "my-slug"));
    }

    @Test
    void buildCanonicalUrl_returnsEmptyWhenSlugBlank() {
        assertEquals("", seoService.buildCanonicalUrl("https://myblog.com", ""));
        assertEquals("", seoService.buildCanonicalUrl("https://myblog.com", null));
    }

    // ── buildJsonLdStructuredData ─────────────────────────────────────────

    @Test
    void buildJsonLd_containsRequiredFields() {
        Map<String, Object> data = seoService.buildJsonLdStructuredData(
                "My Article Title",
                "A short summary.",
                "https://myblog.com/post/my-article-title",
                List.of("spring boot", "jwt"),
                "adminUser",
                "2024-01-01T00:00:00Z",
                "2024-01-01T00:00:00Z",
                1200,
                6,
                "Spring Security",
                List.of("JWT"),
                "https://myblog.com",
                "es");

        assertEquals("https://schema.org", data.get("@context"));
        assertEquals("TechArticle", data.get("@type"));
        assertEquals("My Article Title", data.get("headline"));
        assertEquals("A short summary.", data.get("description"));
        assertEquals("es", data.get("inLanguage"));
        assertEquals(1200, data.get("wordCount"));
        assertEquals("PT6M", data.get("timeRequired"));
        assertEquals("Spring Security", data.get("articleSection"));
        assertEquals("spring boot, jwt", data.get("keywords"));
        assertTrue(data.containsKey("author"));
        assertTrue(data.containsKey("publisher"));
        assertTrue(data.containsKey("about"));
        assertTrue(data.containsKey("url"));
        assertTrue(data.containsKey("mainEntityOfPage"));
    }

    @Test
    void buildJsonLd_truncatesLongHeadline() {
        String longTitle = "A".repeat(120);
        Map<String, Object> data = seoService.buildJsonLdStructuredData(
                longTitle, "summary", "", List.of(), "author",
                "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z",
                100, 1, "Category", List.of(), "", "en");

        String headline = (String) data.get("headline");
        assertTrue(headline.length() <= 110, "Headline should be truncated to 110 characters");
    }

    @Test
    void buildJsonLd_noPublisherWhenSiteBlank() {
        Map<String, Object> data = seoService.buildJsonLdStructuredData(
                "Title", "Summary", "", List.of(), "author",
                "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z",
                100, 1, "Category", List.of(), "", "en");

        assertFalse(data.containsKey("publisher"), "Should not have publisher when site is blank");
    }

    @Test
    void buildJsonLd_noAboutWhenTagsEmpty() {
        Map<String, Object> data = seoService.buildJsonLdStructuredData(
                "Title", "Summary", "https://myblog.com/post/title",
                List.of(), "author",
                "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z",
                100, 1, "Category", List.of(), "https://myblog.com", "en");

        assertFalse(data.containsKey("about"), "Should not have 'about' when tag list is empty");
    }

    @SuppressWarnings("unchecked")
    @Test
    void buildJsonLd_authorContainsName() {
        Map<String, Object> data = seoService.buildJsonLdStructuredData(
                "Title", "Summary", "", List.of(), "jnfz92",
                "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z",
                100, 1, "Category", List.of(), "", "es");

        Map<String, Object> author = (Map<String, Object>) data.get("author");
        assertEquals("jnfz92", author.get("name"));
    }
}
