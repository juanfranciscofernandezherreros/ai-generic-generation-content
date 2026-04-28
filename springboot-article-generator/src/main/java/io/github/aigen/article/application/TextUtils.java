package io.github.aigen.article.application;

import java.text.Normalizer;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Text processing utilities for article generation.
 *
 * <p>Mirrors the functionality of the Python {@code utils.py} and {@code html_utils.py} modules:
 * slug generation, title similarity detection, HTML escaping, word counting and reading time
 * estimation.
 */
public class TextUtils {

    private static final int WORDS_PER_MINUTE = 230;

    // ── Slug ──────────────────────────────────────────────────────────────

    /**
     * Converts {@code text} into a URL-safe, lowercase slug.
     *
     * <ol>
     *   <li>NFD-normalises to separate base characters from diacritics.</li>
     *   <li>Removes combining (accent) characters.</li>
     *   <li>Lower-cases the result.</li>
     *   <li>Replaces sequences of non-alphanumeric characters with {@code -}.</li>
     *   <li>Strips leading/trailing hyphens.</li>
     * </ol>
     *
     * @param text input text (may contain Unicode, spaces, and symbols)
     * @return clean, URL-safe slug
     */
    public String slugify(String text) {
        if (text == null || text.isBlank()) return "";
        String normalised = Normalizer.normalize(text, Normalizer.Form.NFD);
        normalised = normalised.replaceAll("\\p{M}", "");
        normalised = normalised.toLowerCase().strip();
        normalised = normalised.replaceAll("[^a-z0-9]+", "-");
        return normalised.replaceAll("^-+|-+$", "");
    }

    // ── Similarity ────────────────────────────────────────────────────────

    /**
     * Normalises a string for similarity comparison: removes diacritics, lower-cases,
     * replaces non-alphanumeric characters with spaces, and collapses whitespace.
     */
    public String normaliseForSimilarity(String s) {
        if (s == null || s.isBlank()) return "";
        String n = Normalizer.normalize(s, Normalizer.Form.NFD);
        n = n.replaceAll("\\p{M}", "");
        n = n.toLowerCase();
        n = n.replaceAll("[\\W_]+", " ");
        return n.replaceAll("\\s+", " ").strip();
    }

    /**
     * Computes the similarity ratio between {@code a} and {@code b} in the range [0.0, 1.0]
     * using a simple longest-common-subsequence based metric (SequenceMatcher equivalent).
     *
     * @param a first string
     * @param b second string
     * @return similarity ratio (0.0 = completely different, 1.0 = identical)
     */
    public double similarityRatio(String a, String b) {
        String aNorm = normaliseForSimilarity(a);
        String bNorm = normaliseForSimilarity(b);
        if (aNorm.isEmpty() || bNorm.isEmpty()) return 0.0;

        char[] aChars = aNorm.toCharArray();
        char[] bChars = bNorm.toCharArray();
        int m = aChars.length;
        int n = bChars.length;
        int[][] dp = new int[m + 1][n + 1];
        for (int i = 1; i <= m; i++) {
            for (int j = 1; j <= n; j++) {
                if (aChars[i - 1] == bChars[j - 1]) {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                } else {
                    dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
                }
            }
        }
        int lcs = dp[m][n];
        return (2.0 * lcs) / (m + n);
    }

    /**
     * Returns {@code true} if {@code title} is too similar to any entry in {@code candidates}.
     *
     * @param title      candidate title to check
     * @param candidates list of existing titles
     * @param threshold  similarity threshold (0.0 – 1.0)
     * @return {@code true} when at least one candidate reaches the threshold
     */
    public boolean isTooSimilar(String title, List<String> candidates, double threshold) {
        if (title == null || candidates == null) return false;
        for (String c : candidates) {
            if (similarityRatio(title, c) >= threshold) return true;
        }
        return false;
    }

    // ── HTML utilities ────────────────────────────────────────────────────

    /**
     * Escapes HTML special characters ({@code &}, {@code <}, {@code >}) in {@code s}.
     */
    public String htmlEscape(String s) {
        if (s == null) return "";
        return s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;");
    }

    /**
     * Strips all HTML tags from {@code html} and returns the plain text with normalised
     * whitespace.
     */
    public String extractPlainText(String html) {
        if (html == null || html.isBlank()) return "";
        String text = html.replaceAll("<[^>]+>", " ");
        return text.replaceAll("\\s+", " ").strip();
    }

    /**
     * Counts the number of words in the plain text extracted from {@code html}.
     */
    public int countWords(String html) {
        String text = extractPlainText(html);
        if (text.isBlank()) return 0;
        return text.split("\\s+").length;
    }

    /**
     * Estimates the reading time of {@code bodyHtml} in minutes (minimum 1).
     *
     * <p>Uses a reading speed of {@value #WORDS_PER_MINUTE} words per minute, which is
     * typical for technical content.
     */
    public int estimateReadingTime(String bodyHtml) {
        int words = countWords(bodyHtml);
        return Math.max(1, (int) Math.ceil((double) words / WORDS_PER_MINUTE));
    }

    /**
     * Replaces the first {@code <h1>} element in {@code body} with {@code title},
     * or prepends a new {@code <h1>} when none exists.
     *
     * @param body  HTML body of the article
     * @param title new title text (will be HTML-escaped)
     * @return HTML body with the {@code <h1>} updated
     */
    public String replaceH1(String body, String title) {
        if (body == null) body = "";
        String escaped = htmlEscape(title);
        Pattern h1Pattern = Pattern.compile("<h1[^>]*>.*?</h1>",
                Pattern.DOTALL | Pattern.CASE_INSENSITIVE);
        java.util.regex.Matcher m = h1Pattern.matcher(body);
        if (m.find()) {
            return m.replaceFirst("<h1>" + escaped + "</h1>");
        }
        return "<h1>" + escaped + "</h1>\n" + body;
    }
}
