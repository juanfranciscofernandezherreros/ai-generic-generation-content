package io.github.aigen.shared.ai;

/**
 * Narrow read-only view of the AI-related configuration consumed by the
 * infrastructure adapters.
 *
 * <p>Decouples the per-provider clients ({@code OpenAiRestClient},
 * {@code GeminiRestClient}, {@code OllamaRestClient}, {@code LangChain4jClient}) from the
 * full {@code ArticleGeneratorProperties} object — they only need to know which provider
 * is active, the model name, and the credentials / base URLs of the supported back-ends.
 */
public interface AiConfig {

    /** Configured AI provider (may be {@link AiProvider#AUTO}). */
    AiProvider getProvider();

    /** AI model identifier (e.g. {@code gpt-4o}, {@code gemini-2.5-pro}). */
    String getModel();

    /** OpenAI API key, or {@code null} when not configured. */
    String getOpenaiApiKey();

    /** Google Gemini API key, or {@code null} when not configured. */
    String getGeminiApiKey();

    /** Ollama base URL, or {@code null} when not configured. */
    String getOllamaBaseUrl();
}
