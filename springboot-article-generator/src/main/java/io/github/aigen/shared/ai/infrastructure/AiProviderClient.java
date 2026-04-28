package io.github.aigen.shared.ai.infrastructure;

import io.github.aigen.shared.ai.AiConfig;
import io.github.aigen.shared.ai.AiProvider;

/**
 * Strategy interface for a single AI back-end (OpenAI REST, Gemini REST, Ollama REST,
 * LangChain4j {@code ChatModel}, …).
 *
 * <p>Implementations are stateless transport adapters: they translate a
 * {@code (systemMsg, userPrompt, maxTokens, temperature)} call into a provider-specific
 * HTTP request (or LangChain4j call) and return the raw text reply.
 *
 * <p>The {@code CompositeAiClient} selects the appropriate {@code AiProviderClient}
 * at runtime based on the resolved {@link AiProvider}.
 */
public interface AiProviderClient {

    /**
     * @return {@code true} if this client is able to serve the given resolved provider.
     */
    boolean supports(AiProvider resolvedProvider, AiConfig config);

    /**
     * Sends the prompt to the underlying back-end and returns its raw textual response.
     *
     * @throws RuntimeException if the call fails or the response is empty
     */
    String generate(String systemMsg, String userPrompt, int maxTokens, double temperature);
}
