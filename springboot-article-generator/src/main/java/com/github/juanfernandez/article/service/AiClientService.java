package com.github.juanfernandez.article.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.juanfernandez.article.config.ArticleGeneratorProperties;
import com.github.juanfernandez.article.model.AiProvider;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * HTTP client for AI provider APIs (OpenAI, Google Gemini, Ollama).
 *
 * <p>This service is responsible for:
 * <ul>
 *   <li>Detecting the active AI provider based on {@link ArticleGeneratorProperties#getProvider()}.</li>
 *   <li>Making HTTP POST requests to the appropriate API endpoint.</li>
 *   <li>Extracting the text content from the AI response.</li>
 *   <li>Extracting JSON blocks from free-form AI responses.</li>
 * </ul>
 *
 * <p><strong>OpenAI / Ollama</strong> — uses the standard OpenAI Chat Completions API
 * ({@code POST /v1/chat/completions}).  Ollama exposes an OpenAI-compatible endpoint so the same
 * request format is used for both.
 *
 * <p><strong>Google Gemini</strong> — uses the Google AI REST API
 * ({@code POST .../models/{model}:generateContent}).
 */
public class AiClientService {

    private static final Logger log = LoggerFactory.getLogger(AiClientService.class);

    private static final String OPENAI_BASE_URL = "https://api.openai.com";
    private static final String GEMINI_BASE_URL  = "https://generativelanguage.googleapis.com";

    private final ArticleGeneratorProperties properties;
    private final ObjectMapper objectMapper;

    public AiClientService(ArticleGeneratorProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    // ── Provider detection ────────────────────────────────────────────────

    /**
     * Returns {@code true} when the active provider is Google Gemini.
     */
    public boolean isGeminiProvider() {
        AiProvider p = properties.getProvider();
        if (p == AiProvider.GEMINI) return true;
        if (p == AiProvider.OPENAI || p == AiProvider.OLLAMA) return false;
        return properties.getModel() != null && properties.getModel().toLowerCase().startsWith("gemini");
    }

    /**
     * Returns {@code true} when the active provider is Ollama.
     */
    public boolean isOllamaProvider() {
        AiProvider p = properties.getProvider();
        if (p == AiProvider.OLLAMA) return true;
        if (p == AiProvider.OPENAI || p == AiProvider.GEMINI) return false;
        String baseUrl = properties.getOllamaBaseUrl();
        return baseUrl != null && !baseUrl.isBlank();
    }

    // ── Main generation method ────────────────────────────────────────────

    /**
     * Sends {@code userPrompt} to the configured AI provider and returns the raw text response.
     *
     * @param systemMsg   system / instruction message for the AI
     * @param userPrompt  user prompt text
     * @param maxTokens   maximum output tokens
     * @param temperature generation temperature (0.0 – 1.0)
     * @return raw text returned by the AI
     * @throws RuntimeException if the API call fails or returns no content
     */
    public String generate(String systemMsg, String userPrompt, int maxTokens, double temperature) {
        if (isGeminiProvider()) {
            return callGemini(systemMsg, userPrompt, maxTokens, temperature);
        } else if (isOllamaProvider()) {
            return callOpenAiCompatible(
                    resolveOllamaBaseUrl(),
                    "ollama",          // placeholder key
                    systemMsg, userPrompt, maxTokens, temperature);
        } else {
            return callOpenAiCompatible(
                    OPENAI_BASE_URL,
                    properties.getOpenaiApiKey(),
                    systemMsg, userPrompt, maxTokens, temperature);
        }
    }

    // ── JSON extraction ───────────────────────────────────────────────────

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

        // 1. Try fenced ```json { ... }```
        Pattern fence = Pattern.compile("```(?:json)?\\s*(\\{.*?\\})\\s*```",
                Pattern.DOTALL | Pattern.CASE_INSENSITIVE);
        Matcher fm = fence.matcher(text);
        if (fm.find()) return fm.group(1).strip();

        // 2. Try bare { ... }
        Pattern brace = Pattern.compile("\\{.*\\}", Pattern.DOTALL);
        Matcher bm = brace.matcher(text);
        return bm.find() ? bm.group(0).strip() : text.strip();
    }

    /**
     * Parses a JSON string with tolerance for typographic quotes ({@code \u201c}, {@code \u201d},
     * {@code \u2019}).
     *
     * @param json JSON string to parse
     * @return parsed {@link JsonNode}
     * @throws RuntimeException if the JSON is invalid even after quote normalisation
     */
    public JsonNode safeJsonParse(String json) {
        try {
            return objectMapper.readTree(json);
        } catch (Exception first) {
            // Normalise typographic quotes and retry
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

    // ── OpenAI / Ollama ───────────────────────────────────────────────────

    private String callOpenAiCompatible(String baseUrl, String apiKey,
                                         String systemMsg, String userPrompt,
                                         int maxTokens, double temperature) {
        RestClient client = RestClient.builder()
                .baseUrl(baseUrl)
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .defaultHeader(HttpHeaders.AUTHORIZATION, "Bearer " + apiKey)
                .build();

        Map<String, Object> requestBody = Map.of(
                "model", properties.getModel(),
                "messages", List.of(
                        Map.of("role", "system", "content", systemMsg),
                        Map.of("role", "user", "content", userPrompt)
                ),
                "max_tokens", maxTokens,
                "temperature", temperature
        );

        log.debug("Calling OpenAI-compatible API at {} with model={}", baseUrl, properties.getModel());

        try {
            String responseBody = client.post()
                    .uri("/v1/chat/completions")
                    .body(requestBody)
                    .retrieve()
                    .body(String.class);

            return extractOpenAiContent(responseBody);
        } catch (Exception e) {
            throw new RuntimeException("AI API call failed (" + baseUrl + "): " + e.getMessage(), e);
        }
    }

    private String extractOpenAiContent(String responseBody) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            JsonNode content = root.path("choices").path(0).path("message").path("content");
            if (content.isMissingNode() || content.isNull()) {
                throw new RuntimeException("AI response contained no content. Response: "
                        + responseBody.substring(0, Math.min(300, responseBody.length())));
            }
            return content.asText();
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse AI response: " + e.getMessage(), e);
        }
    }

    // ── Google Gemini ─────────────────────────────────────────────────────

    private String callGemini(String systemMsg, String userPrompt, int maxTokens, double temperature) {
        String apiKey = properties.getGeminiApiKey();
        if (apiKey == null || apiKey.isBlank()) {
            throw new RuntimeException(
                    "article-generator.gemini-api-key is not configured. "
                    + "Set it in application.properties or via the GEMINI_API_KEY environment variable.");
        }

        RestClient client = RestClient.builder()
                .baseUrl(GEMINI_BASE_URL)
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .build();

        Map<String, Object> requestBody = Map.of(
                "contents", List.of(
                        Map.of("role", "user",
                               "parts", List.of(Map.of("text", userPrompt)))
                ),
                "systemInstruction", Map.of(
                        "parts", List.of(Map.of("text", systemMsg))
                ),
                "generationConfig", Map.of(
                        "maxOutputTokens", maxTokens,
                        "temperature", temperature
                )
        );

        String uri = "/v1beta/models/" + properties.getModel() + ":generateContent?key=" + apiKey;
        log.debug("Calling Gemini API with model={}", properties.getModel());

        try {
            String responseBody = client.post()
                    .uri(uri)
                    .body(requestBody)
                    .retrieve()
                    .body(String.class);

            return extractGeminiContent(responseBody);
        } catch (Exception e) {
            throw new RuntimeException("Gemini API call failed: " + e.getMessage(), e);
        }
    }

    private String extractGeminiContent(String responseBody) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            JsonNode text = root.path("candidates").path(0)
                    .path("content").path("parts").path(0).path("text");
            if (text.isMissingNode() || text.isNull()) {
                throw new RuntimeException("Gemini response contained no text. Response: "
                        + responseBody.substring(0, Math.min(300, responseBody.length())));
            }
            return text.asText();
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse Gemini response: " + e.getMessage(), e);
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    private String resolveOllamaBaseUrl() {
        String url = properties.getOllamaBaseUrl();
        if (url == null || url.isBlank()) {
            url = "http://localhost:11434";
        }
        // If the URL already ends with /v1 we strip it here so /v1/chat/completions is appended once
        return url.replaceAll("/v1/?$", "");
    }
}
