package com.github.juanfernandez.article.model;

/**
 * Supported AI providers for article generation.
 *
 * <ul>
 *   <li>{@link #AUTO}      — Auto-detect: Gemini if model starts with {@code gemini-},
 *       Ollama if {@code article-generator.ollama-base-url} is set, otherwise OpenAI.</li>
 *   <li>{@link #OPENAI}    — Force OpenAI (GPT models via {@code api.openai.com}).</li>
 *   <li>{@link #GEMINI}    — Force Google Gemini (via {@code generativelanguage.googleapis.com}).</li>
 *   <li>{@link #OLLAMA}    — Force Ollama local LLM server (OpenAI-compatible API).</li>
 *   <li>{@link #ANTHROPIC} — Force Anthropic Claude (requires LangChain4j
 *       {@code langchain4j-anthropic-spring-boot-starter}).</li>
 * </ul>
 */
public enum AiProvider {
    AUTO,
    OPENAI,
    GEMINI,
    OLLAMA,
    ANTHROPIC
}
