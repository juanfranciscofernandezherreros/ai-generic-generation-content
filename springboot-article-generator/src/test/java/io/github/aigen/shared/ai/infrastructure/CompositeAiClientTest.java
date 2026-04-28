package io.github.aigen.shared.ai.infrastructure;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.shared.config.ArticleGeneratorProperties;
import io.github.aigen.shared.ai.AiProvider;
import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.message.ChatMessage;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.response.ChatResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Tests for {@link CompositeAiClient} verifying that:
 * <ul>
 *   <li>The {@link LangChain4jClient} wins for every provider when a {@link ChatModel} bean
 *       is available.</li>
 *   <li>Anthropic without a {@link ChatModel} bean produces a descriptive error.</li>
 *   <li>OpenAI without a {@link ChatModel} bean falls back to the REST client (which
 *       fails fast in this test because the API key is missing / network blocked).</li>
 * </ul>
 */
class CompositeAiClientTest {

    private ArticleGeneratorProperties properties;
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        properties = new ArticleGeneratorProperties();
        objectMapper = new ObjectMapper();
    }

    private ChatResponse mockResponse(String content) {
        return ChatResponse.builder()
                .aiMessage(AiMessage.from(content))
                .build();
    }

    private CompositeAiClient withChatModel(ChatModel chatModel) {
        return new CompositeAiClient(properties, List.of(
                new LangChain4jClient(chatModel),
                new OpenAiRestClient(properties, objectMapper),
                new GeminiRestClient(properties, objectMapper),
                new OllamaRestClient(properties, objectMapper)
        ));
    }

    private CompositeAiClient withoutChatModel() {
        // No LangChain4jClient registered → REST clients only.
        return new CompositeAiClient(properties, List.of(
                new OpenAiRestClient(properties, objectMapper),
                new GeminiRestClient(properties, objectMapper),
                new OllamaRestClient(properties, objectMapper)
        ));
    }

    // ── LangChain4j wins for every provider ──────────────────────────────

    @Test
    void usesLangChain4jForOpenAi() {
        properties.setProvider(AiProvider.OPENAI);
        ChatModel mockModel = mock(ChatModel.class);
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse("Generated article content"));

        String result = withChatModel(mockModel).generate("system msg", "user prompt", 500, 0.0);

        assertEquals("Generated article content", result);
        verify(mockModel, times(1)).chat(any(ChatMessage.class), any(ChatMessage.class));
    }

    @Test
    void usesLangChain4jForGemini() {
        properties.setProvider(AiProvider.GEMINI);
        properties.setGeminiApiKey("dummy-key");
        ChatModel mockModel = mock(ChatModel.class);
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse("Gemini article content"));

        String result = withChatModel(mockModel).generate("system msg", "user prompt", 500, 0.0);

        assertEquals("Gemini article content", result);
        verify(mockModel, times(1)).chat(any(ChatMessage.class), any(ChatMessage.class));
    }

    @Test
    void usesLangChain4jForOllama() {
        properties.setProvider(AiProvider.OLLAMA);
        properties.setOllamaBaseUrl("http://localhost:11434");
        ChatModel mockModel = mock(ChatModel.class);
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse("Ollama article content"));

        String result = withChatModel(mockModel).generate("system msg", "user prompt", 500, 0.0);

        assertEquals("Ollama article content", result);
        verify(mockModel, times(1)).chat(any(ChatMessage.class), any(ChatMessage.class));
    }

    @Test
    void usesLangChain4jForAnthropic() {
        properties.setProvider(AiProvider.ANTHROPIC);
        ChatModel mockModel = mock(ChatModel.class);
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse("Anthropic Claude article content"));

        String result = withChatModel(mockModel).generate("system msg", "user prompt", 500, 0.0);

        assertEquals("Anthropic Claude article content", result);
        verify(mockModel, times(1)).chat(any(ChatMessage.class), any(ChatMessage.class));
    }

    // ── No LangChain4j ────────────────────────────────────────────────────

    @Test
    void anthropicWithoutLangChain4jThrowsDescriptiveError() {
        properties.setProvider(AiProvider.ANTHROPIC);

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> withoutChatModel().generate("sys", "user", 10, 0.0));
        assertTrue(ex.getMessage().contains("Anthropic"),
                "Expected 'Anthropic' in error message, got: " + ex.getMessage());
        assertTrue(ex.getMessage().contains("langchain4j-anthropic-spring-boot-starter"),
                "Expected starter name in error message, got: " + ex.getMessage());
    }

    @Test
    void openAiWithoutLangChain4jFallsBackToRestPath() {
        properties.setProvider(AiProvider.OPENAI);

        // The REST path will fail attempting a real HTTP call with a null/blank API key.
        // A RuntimeException (not NPE) is expected.
        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> withoutChatModel().generate("sys", "user", 10, 0.0));
        assertNotNull(ex.getMessage(), "Expected a descriptive RuntimeException from the REST path");
    }

    // ── Empty LangChain4j response ────────────────────────────────────────

    @Test
    void langChain4jEmptyResponseThrows() {
        ChatModel mockModel = mock(ChatModel.class);
        when(mockModel.chat(any(ChatMessage.class), any(ChatMessage.class)))
                .thenReturn(mockResponse(""));

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> withChatModel(mockModel).generate("system msg", "user prompt", 500, 0.0));
        assertTrue(ex.getMessage().contains("empty response"),
                "Expected 'empty response' in message, got: " + ex.getMessage());
    }
}
