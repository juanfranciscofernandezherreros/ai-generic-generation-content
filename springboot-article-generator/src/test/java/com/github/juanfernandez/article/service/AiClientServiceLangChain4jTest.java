package com.github.juanfernandez.article.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.juanfernandez.article.config.ArticleGeneratorProperties;
import com.github.juanfernandez.article.model.AiProvider;
import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.message.ChatMessage;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.response.ChatResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for {@link AiClientService} verifying that LangChain4j {@link ChatModel}
 * is used for all four AI providers (OpenAI, Gemini, Ollama, Anthropic) when a bean is available.
 */
class AiClientServiceLangChain4jTest {

    private AiClientService service;
    private ChatModel mockModel;
    private ArticleGeneratorProperties properties;

    @BeforeEach
    void setUp() {
        properties = new ArticleGeneratorProperties();
        mockModel = mock(ChatModel.class);
        service = new AiClientService(properties, new ObjectMapper(), mockModel);
    }

    // ── Helper ────────────────────────────────────────────────────────────

    private ChatResponse mockResponse(String content) {
        return ChatResponse.builder()
                .aiMessage(AiMessage.from(content))
                .build();
    }

    // ── OpenAI ────────────────────────────────────────────────────────────

    @Test
    void generate_usesLangChain4jForOpenAi() {
        properties.setProvider(AiProvider.OPENAI);
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse("Generated article content"));

        String result = service.generate("system msg", "user prompt", 500, 0.0);

        assertEquals("Generated article content", result);
        verify(mockModel, times(1)).chat(any(ChatMessage.class), any(ChatMessage.class));
    }

    // ── Google Gemini ─────────────────────────────────────────────────────

    @Test
    void generate_usesLangChain4jForGemini() {
        properties.setProvider(AiProvider.GEMINI);
        properties.setGeminiApiKey("dummy-key");
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse("Gemini article content"));

        String result = service.generate("system msg", "user prompt", 500, 0.0);

        assertEquals("Gemini article content", result);
        verify(mockModel, times(1)).chat(any(ChatMessage.class), any(ChatMessage.class));
    }

    // ── Ollama ────────────────────────────────────────────────────────────

    @Test
    void generate_usesLangChain4jForOllama() {
        properties.setProvider(AiProvider.OLLAMA);
        properties.setOllamaBaseUrl("http://localhost:11434");
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse("Ollama article content"));

        String result = service.generate("system msg", "user prompt", 500, 0.0);

        assertEquals("Ollama article content", result);
        verify(mockModel, times(1)).chat(any(ChatMessage.class), any(ChatMessage.class));
    }

    // ── Anthropic ─────────────────────────────────────────────────────────

    @Test
    void generate_usesLangChain4jForAnthropic() {
        properties.setProvider(AiProvider.ANTHROPIC);
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse("Anthropic Claude article content"));

        String result = service.generate("system msg", "user prompt", 500, 0.0);

        assertEquals("Anthropic Claude article content", result);
        verify(mockModel, times(1)).chat(any(ChatMessage.class), any(ChatMessage.class));
    }

    @Test
    void generate_throwsDescriptiveErrorForAnthropicWithoutLangChain4j() {
        // Without LangChain4j bean, ANTHROPIC provider should throw a helpful error
        AiClientService noLc4jService = new AiClientService(properties, new ObjectMapper());
        properties.setProvider(AiProvider.ANTHROPIC);

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> noLc4jService.generate("sys", "user", 10, 0.0));
        assertTrue(ex.getMessage().contains("Anthropic"),
                "Expected 'Anthropic' in error message, got: " + ex.getMessage());
        assertTrue(ex.getMessage().contains("langchain4j-anthropic-spring-boot-starter"),
                "Expected starter name in error message, got: " + ex.getMessage());
    }

    // ── Empty response ────────────────────────────────────────────────────

    @Test
    void generate_throwsWhenLangChain4jReturnsEmpty() {
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse(""));

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> service.generate("system msg", "user prompt", 500, 0.0));
        assertTrue(ex.getMessage().contains("empty response"),
                "Expected 'empty response' in message, got: " + ex.getMessage());
    }

    // ── Fallback (no LangChain4j bean) ────────────────────────────────────

    @Test
    void generate_withoutLangChain4jFallsBackToRestPathForOpenAi() {
        // Without LangChain4j, service is created with the two-arg constructor (chatModel == null)
        AiClientService noLc4jService = new AiClientService(properties, new ObjectMapper());

        // The service should take the REST fallback path, which will fail attempting a real
        // HTTP call with a null/blank API key. A RuntimeException (not NPE) is expected.
        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> noLc4jService.generate("sys", "user", 10, 0.0));
        assertNotNull(ex.getMessage(), "Expected a descriptive RuntimeException from the REST path");
    }
}
