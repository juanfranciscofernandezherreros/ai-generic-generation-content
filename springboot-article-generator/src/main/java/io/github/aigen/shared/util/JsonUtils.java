package io.github.aigen.shared.util;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Shared utility for extracting and parsing JSON from AI responses.
 *
 * <p>Both the article and pregunta bounded contexts need to extract JSON blocks from raw
 * AI output and parse them tolerantly.  This class centralises that logic in the shared
 * kernel so neither application service needs to depend on the infrastructure adapter.
 */
public class JsonUtils {

    private final ObjectMapper objectMapper;

    public JsonUtils(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    /**
     * Extracts the first JSON object ({@code {...}}) from an AI response string.
     *
     * <p>Supports two common response formats:
     * <ol>
     *   <li>Fenced code block: <code>```json { ... }```</code></li>
     *   <li>Bare JSON embedded anywhere in the text.</li>
     * </ol>
     *
     * @param text raw AI response
     * @return extracted JSON string, or the original {@code text} when no object is found
     */
    public String extractJsonBlock(String text) {
        if (text == null || text.isBlank()) return "";

        Pattern fence = Pattern.compile("```(?:json)?\\s*(\\{.*?\\})\\s*```",
                Pattern.DOTALL | Pattern.CASE_INSENSITIVE);
        Matcher fm = fence.matcher(text);
        if (fm.find()) return fm.group(1).strip();

        Pattern brace = Pattern.compile("\\{.*\\}", Pattern.DOTALL);
        Matcher bm = brace.matcher(text);
        return bm.find() ? bm.group(0).strip() : text.strip();
    }

    /**
     * Parses a JSON string with tolerance for typographic quotes
     * ({@code \u201c}, {@code \u201d}, {@code \u2019}).
     *
     * @param json JSON string to parse
     * @return parsed {@link JsonNode}
     * @throws RuntimeException if the JSON is invalid even after quote normalisation
     */
    public JsonNode safeJsonParse(String json) {
        try {
            return objectMapper.readTree(json);
        } catch (Exception first) {
            String normalised = json
                    .replace("\u201c", "\"")
                    .replace("\u201d", "\"")
                    .replace("\u2019", "'");
            try {
                return objectMapper.readTree(normalised);
            } catch (Exception second) {
                throw new RuntimeException("Invalid JSON from AI: " + first.getMessage()
                        + " | preview: " + json.substring(0, Math.min(300, json.length())), second);
            }
        }
    }
}
