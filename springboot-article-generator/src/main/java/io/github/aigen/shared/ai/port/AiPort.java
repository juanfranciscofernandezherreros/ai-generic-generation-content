package io.github.aigen.shared.ai.port;

/**
 * Output port (secondary port) for AI text generation.
 *
 * <p>This interface belongs to the shared kernel and is used by both the article and
 * pregunta bounded contexts to decouple their application logic from any specific AI
 * provider (OpenAI, Gemini, Ollama, Anthropic).
 *
 * <p>The infrastructure adapter {@code AiClientAdapter} provides the concrete implementation.
 */
public interface AiPort {

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
    String generate(String systemMsg, String userPrompt, int maxTokens, double temperature);
}
