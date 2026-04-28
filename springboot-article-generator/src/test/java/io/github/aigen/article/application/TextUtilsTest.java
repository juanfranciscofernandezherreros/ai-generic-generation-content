package io.github.aigen.article.application;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link TextUtils}.
 */
class TextUtilsTest {

    private TextUtils utils;

    @BeforeEach
    void setUp() {
        utils = new TextUtils();
    }

    // ── slugify ───────────────────────────────────────────────────────────

    @Test
    void slugify_convertsAccentedCharacters() {
        assertEquals("como-usar-data-en-lombok", utils.slugify("Cómo usar @Data en Lombok"));
    }

    @Test
    void slugify_handlesSpringBootTitle() {
        assertEquals("spring-boot-3", utils.slugify("  Spring Boot 3  "));
    }

    @Test
    void slugify_lowercasesInput() {
        assertEquals("java-streams", utils.slugify("Java Streams"));
    }

    @Test
    void slugify_stripsLeadingAndTrailingHyphens() {
        assertEquals("hello-world", utils.slugify("--hello world--"));
    }

    @Test
    void slugify_nullReturnsEmpty() {
        assertEquals("", utils.slugify(null));
    }

    @Test
    void slugify_blankReturnsEmpty() {
        assertEquals("", utils.slugify("   "));
    }

    // ── similarity ────────────────────────────────────────────────────────

    @Test
    void similarityRatio_identicalStrings() {
        assertEquals(1.0, utils.similarityRatio("Spring Boot JWT", "Spring Boot JWT"), 0.001);
    }

    @Test
    void similarityRatio_completelyDifferent() {
        double ratio = utils.similarityRatio("Spring Boot", "Kubernetes Operators");
        assertTrue(ratio < 0.5, "Ratio should be low for unrelated titles, was: " + ratio);
    }

    @Test
    void similarityRatio_nearlyIdentical() {
        double ratio = utils.similarityRatio(
                "Spring Boot JWT Authentication",
                "Spring Boot JWT Autenticación");
        assertTrue(ratio >= 0.7, "Near-identical titles should have high ratio, was: " + ratio);
    }

    @Test
    void similarityRatio_emptyString() {
        assertEquals(0.0, utils.similarityRatio("", "anything"), 0.001);
    }

    @Test
    void isTooSimilar_detectsDuplicate() {
        List<String> existing = List.of("Spring Boot JWT Authentication Guide");
        assertTrue(utils.isTooSimilar("Spring Boot JWT Authentication Guide", existing, 0.86));
    }

    @Test
    void isTooSimilar_allowsDifferentTitle() {
        List<String> existing = List.of("Spring Boot JWT Authentication Guide");
        assertFalse(utils.isTooSimilar("Kubernetes Pod Scheduling Best Practices", existing, 0.86));
    }

    @Test
    void isTooSimilar_emptyListReturnsFalse() {
        assertFalse(utils.isTooSimilar("Any Title", List.of(), 0.86));
    }

    // ── HTML utilities ────────────────────────────────────────────────────

    @Test
    void htmlEscape_escapesAmpersand() {
        assertEquals("a &amp; b", utils.htmlEscape("a & b"));
    }

    @Test
    void htmlEscape_escapesAngleBrackets() {
        assertEquals("&lt;div&gt;", utils.htmlEscape("<div>"));
    }

    @Test
    void htmlEscape_nullReturnsEmpty() {
        assertEquals("", utils.htmlEscape(null));
    }

    @Test
    void extractPlainText_stripsHtmlTags() {
        String html = "<h1>Title</h1><p>Some <strong>content</strong> here.</p>";
        String text = utils.extractPlainText(html);
        assertFalse(text.contains("<"), "Should not contain HTML tags");
        assertTrue(text.contains("Title"));
        assertTrue(text.contains("content"));
    }

    @Test
    void countWords_countsWordsInHtml() {
        String html = "<p>One two three four five</p>";
        assertEquals(5, utils.countWords(html));
    }

    @Test
    void countWords_emptyReturnsZero() {
        assertEquals(0, utils.countWords(""));
        assertEquals(0, utils.countWords(null));
    }

    @Test
    void estimateReadingTime_minimumOneMinute() {
        assertEquals(1, utils.estimateReadingTime("<p>Short.</p>"));
    }

    @Test
    void estimateReadingTime_calculatesCorrectly() {
        // 230 words should take exactly 1 minute
        String html = "<p>" + "word ".repeat(230) + "</p>";
        assertEquals(1, utils.estimateReadingTime(html));

        // 231 words should round up to 2 minutes
        html = "<p>" + "word ".repeat(231) + "</p>";
        assertEquals(2, utils.estimateReadingTime(html));
    }

    // ── replaceH1 ─────────────────────────────────────────────────────────

    @Test
    void replaceH1_replacesExistingH1() {
        String body = "<h1>Old Title</h1><p>Body text</p>";
        String result = utils.replaceH1(body, "New Title");
        assertTrue(result.contains("<h1>New Title</h1>"));
        assertFalse(result.contains("Old Title"));
    }

    @Test
    void replaceH1_prependsWhenNoH1Exists() {
        String body = "<p>Body text</p>";
        String result = utils.replaceH1(body, "My Title");
        assertTrue(result.startsWith("<h1>My Title</h1>"));
        assertTrue(result.contains("<p>Body text</p>"));
    }

    @Test
    void replaceH1_escapesHtmlInTitle() {
        String body = "<h1>Old</h1>";
        String result = utils.replaceH1(body, "Title <with> special &amp; chars");
        assertTrue(result.contains("&lt;with&gt;"));
        assertTrue(result.contains("&amp;amp;"));
    }
}
