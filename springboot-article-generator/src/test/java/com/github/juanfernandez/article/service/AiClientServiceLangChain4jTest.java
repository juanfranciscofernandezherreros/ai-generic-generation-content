package com.github.juanfernandez.article.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.juanfernandez.article.config.ArticleGeneratorProperties;
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
 * Unit tests for {@link AiClientService} using a mocked LangChain4j {@link ChatModel}.
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

    @Test
    void generate_usesLangChain4jForOpenAi() {
        String expectedContent = "Generated article content";
        ChatResponse mockResponse = ChatResponse.builder()
                .aiMessage(AiMessage.from(expectedContent))
                .build();
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse);

        String result = service.generate("system msg", "user prompt", 500, 0.0);

        assertEquals(expectedContent, result);
        verify(mockModel, times(1)).chat(any(ChatMessage.class), any(ChatMessage.class));
    }

    @Test
    void generate_throwsWhenLangChain4jReturnsEmpty() {
        ChatResponse mockResponse = ChatResponse.builder()
                .aiMessage(AiMessage.from(""))
                .build();
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse);

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> service.generate("system msg", "user prompt", 500, 0.0));
        assertTrue(ex.getMessage().contains("empty response"),
                "Expected 'empty response' in message, got: " + ex.getMessage());
    }

    @Test
    void generate_withoutLangChain4jFallsBackToRestPathForOpenAi() {
        // Without LangChain4j, service is created with the two-arg constructor (chatModel == null)
        AiClientService noLc4jService = new AiClientService(properties, new ObjectMapper());

        // The service should take the REST path (chatModel is null), which means it will attempt
        // a real HTTP call with a null/blank API key.  The REST client wraps failures in RuntimeException,
        // so we just verify that a RuntimeException is thrown (no NPE from a null chatModel).
        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> noLc4jService.generate("sys", "user", 10, 0.0));
        assertNotNull(ex.getMessage(), "Expected a descriptive RuntimeException from the REST path");
    }

    @Test
    void generate_geminiProviderDoesNotUseLangChain4j() {
        properties.setProvider(com.github.juanfernandez.article.model.AiProvider.GEMINI);
        properties.setGeminiApiKey("dummy-key");

        // Gemini path will call REST which will fail with a connection error — that's fine.
        // The important thing is that the LangChain4j mock is never invoked.
        assertThrows(RuntimeException.class,
                () -> service.generate("sys", "user", 10, 0.0));
        verify(mockModel, never()).chat(any(ChatMessage.class), any(ChatMessage.class));
    }
}
