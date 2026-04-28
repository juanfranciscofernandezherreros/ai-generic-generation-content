package io.github.aigen.shared.ai.infrastructure;

import io.github.aigen.shared.ai.AiConfig;
import io.github.aigen.shared.ai.AiProvider;
import dev.langchain4j.data.message.SystemMessage;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.response.ChatResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * {@link AiProviderClient} that delegates to a LangChain4j {@link ChatModel} bean.
 *
 * <p>When a {@code ChatModel} bean is present in the application context it is preferred
 * for <em>every</em> provider — OpenAI, Google Gemini, Ollama and Anthropic — keeping the
 * REST clients only as a fallback for the first three.
 */
public class LangChain4jClient implements AiProviderClient {

    private static final Logger log = LoggerFactory.getLogger(LangChain4jClient.class);

    private final ChatModel chatModel;

    public LangChain4jClient(ChatModel chatModel) {
        this.chatModel = chatModel;
    }

    @Override
    public boolean supports(AiProvider resolvedProvider, AiConfig config) {
        // Whenever a ChatModel bean is provided, route every provider through LangChain4j.
        return chatModel != null;
    }

    @Override
    public String generate(String systemMsg, String userPrompt, int maxTokens, double temperature) {
        log.debug("Calling AI provider via LangChain4j ChatModel");
        try {
            ChatResponse response = chatModel.chat(
                    SystemMessage.from(systemMsg),
                    UserMessage.from(userPrompt));
            String content = response.aiMessage().text();
            if (content == null || content.isBlank()) {
                throw new RuntimeException("LangChain4j returned an empty response.");
            }
            return content;
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("LangChain4j call failed: " + e.getMessage(), e);
        }
    }
}
