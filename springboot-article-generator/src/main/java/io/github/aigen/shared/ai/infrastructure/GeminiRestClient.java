package io.github.aigen.shared.ai.infrastructure;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.shared.ai.AiConfig;
import io.github.aigen.shared.ai.AiProvider;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

/**
 * REST client for Google Gemini's {@code generativelanguage.googleapis.com} endpoint.
 *
 * <p>Used as a fallback when no LangChain4j {@link dev.langchain4j.model.chat.ChatModel}
 * bean is available.
 */
public class GeminiRestClient implements AiProviderClient {

    private static final Logger log = LoggerFactory.getLogger(GeminiRestClient.class);
    private static final String BASE_URL = "https://generativelanguage.googleapis.com";

    private final AiConfig config;
    private final ObjectMapper objectMapper;

    public GeminiRestClient(AiConfig config, ObjectMapper objectMapper) {
        this.config = config;
        this.objectMapper = objectMapper;
    }

    @Override
    public boolean supports(AiProvider resolvedProvider, AiConfig config) {
        return resolvedProvider == AiProvider.GEMINI;
    }

    @Override
    public String generate(String systemMsg, String userPrompt, int maxTokens, double temperature) {
        String apiKey = config.getGeminiApiKey();
        if (apiKey == null || apiKey.isBlank()) {
            throw new RuntimeException(
                    "article-generator.gemini-api-key is not configured. "
                    + "Set it in application.properties or via the GEMINI_API_KEY environment variable.");
        }

        RestClient client = RestClient.builder()
                .baseUrl(BASE_URL)
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

        String uri = "/v1beta/models/" + config.getModel() + ":generateContent?key=" + apiKey;
        log.debug("Calling Gemini API with model={}", config.getModel());

        try {
            String responseBody = client.post()
                    .uri(uri)
                    .body(requestBody)
                    .retrieve()
                    .body(String.class);
            return extractContent(responseBody);
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Gemini API call failed: " + e.getMessage(), e);
        }
    }

    private String extractContent(String responseBody) {
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
}
