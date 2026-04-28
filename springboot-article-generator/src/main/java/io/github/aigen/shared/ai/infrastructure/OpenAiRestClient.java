package io.github.aigen.shared.ai.infrastructure;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.shared.ai.AiConfig;
import io.github.aigen.shared.ai.AiProvider;

/**
 * REST client for OpenAI's {@code https://api.openai.com/v1/chat/completions} endpoint.
 *
 * <p>Used as a fallback when no LangChain4j {@link dev.langchain4j.model.chat.ChatModel}
 * bean is available.
 */
public class OpenAiRestClient extends OpenAiCompatibleClient {

    private static final String BASE_URL = "https://api.openai.com";

    private final AiConfig config;

    public OpenAiRestClient(AiConfig config, ObjectMapper objectMapper) {
        super(config, objectMapper);
        this.config = config;
    }

    @Override
    protected String baseUrl() {
        return BASE_URL;
    }

    @Override
    protected String apiKey() {
        return config.getOpenaiApiKey();
    }

    @Override
    protected String providerName() {
        return "OpenAI";
    }

    @Override
    public boolean supports(AiProvider resolvedProvider, AiConfig config) {
        return resolvedProvider == AiProvider.OPENAI;
    }
}
