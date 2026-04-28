package io.github.aigen.shared.ai.infrastructure;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.shared.ai.AiConfig;
import io.github.aigen.shared.ai.AiProvider;

/**
 * REST client for an Ollama server (uses the OpenAI-compatible {@code /v1/chat/completions}
 * endpoint).
 *
 * <p>Used as a fallback when no LangChain4j {@link dev.langchain4j.model.chat.ChatModel}
 * bean is available.
 */
public class OllamaRestClient extends OpenAiCompatibleClient {

    private static final String DEFAULT_BASE_URL = "http://localhost:11434";

    private final AiConfig config;

    public OllamaRestClient(AiConfig config, ObjectMapper objectMapper) {
        super(config, objectMapper);
        this.config = config;
    }

    @Override
    protected String baseUrl() {
        String url = config.getOllamaBaseUrl();
        if (url == null || url.isBlank()) {
            url = DEFAULT_BASE_URL;
        }
        return url.replaceAll("/v1/?$", "");
    }

    @Override
    protected String apiKey() {
        // Ollama does not require authentication.
        return null;
    }

    @Override
    protected String providerName() {
        return "Ollama";
    }

    @Override
    public boolean supports(AiProvider resolvedProvider, AiConfig config) {
        return resolvedProvider == AiProvider.OLLAMA;
    }
}
