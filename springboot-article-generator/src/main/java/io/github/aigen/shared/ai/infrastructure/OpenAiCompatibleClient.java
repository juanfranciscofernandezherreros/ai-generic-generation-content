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
 * Base class for OpenAI-compatible REST clients (OpenAI itself, Ollama).
 *
 * <p>Both providers expose the same {@code /v1/chat/completions} contract; the only
 * differences are the base URL and the authentication value.  Subclasses fill those in.
 */
abstract class OpenAiCompatibleClient implements AiProviderClient {

    private static final Logger log = LoggerFactory.getLogger(OpenAiCompatibleClient.class);

    private final AiConfig config;
    private final ObjectMapper objectMapper;

    OpenAiCompatibleClient(AiConfig config, ObjectMapper objectMapper) {
        this.config = config;
        this.objectMapper = objectMapper;
    }

    /** Base URL for the {@code /v1/chat/completions} endpoint. */
    protected abstract String baseUrl();

    /** Bearer token. May be {@code null}/blank for back-ends that don't require auth (Ollama). */
    protected abstract String apiKey();

    /** Provider name used in error messages. */
    protected abstract String providerName();

    @Override
    public String generate(String systemMsg, String userPrompt, int maxTokens, double temperature) {
        RestClient.Builder builder = RestClient.builder()
                .baseUrl(baseUrl())
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE);

        String key = apiKey();
        if (key != null && !key.isBlank()) {
            builder.defaultHeader(HttpHeaders.AUTHORIZATION, "Bearer " + key);
        }
        RestClient client = builder.build();

        Map<String, Object> requestBody = Map.of(
                "model", config.getModel(),
                "messages", List.of(
                        Map.of("role", "system", "content", systemMsg),
                        Map.of("role", "user",   "content", userPrompt)
                ),
                "max_tokens", maxTokens,
                "temperature", temperature
        );

        log.debug("Calling {} API at {} with model={}", providerName(), baseUrl(), config.getModel());

        try {
            String responseBody = client.post()
                    .uri("/v1/chat/completions")
                    .body(requestBody)
                    .retrieve()
                    .body(String.class);
            return extractContent(responseBody);
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException(providerName() + " API call failed: " + e.getMessage(), e);
        }
    }

    private String extractContent(String responseBody) {
        try {
            JsonNode root = objectMapper.readTree(responseBody);
            JsonNode content = root.path("choices").path(0).path("message").path("content");
            if (content.isMissingNode() || content.isNull()) {
                throw new RuntimeException(providerName() + " response contained no content. Response: "
                        + responseBody.substring(0, Math.min(300, responseBody.length())));
            }
            return content.asText();
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Failed to parse " + providerName() + " response: " + e.getMessage(), e);
        }
    }

    /** {@inheritDoc} — default implementation supports the matching {@link AiProvider}. */
    @Override
    public abstract boolean supports(AiProvider resolvedProvider, AiConfig config);
}
