package io.github.aigen;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.shared.ai.AiConfig;
import io.github.aigen.shared.ai.RetryConfig;
import io.github.aigen.shared.ai.infrastructure.CompositeAiClient;
import io.github.aigen.shared.ai.infrastructure.GeminiRestClient;
import io.github.aigen.shared.ai.infrastructure.LangChain4jClient;
import io.github.aigen.shared.ai.infrastructure.OllamaRestClient;
import io.github.aigen.shared.ai.infrastructure.OpenAiRestClient;
import io.github.aigen.shared.ai.infrastructure.RetryingAiPort;
import io.github.aigen.shared.ai.port.AiPort;
import io.github.aigen.shared.config.ArticleGeneratorProperties;
import io.github.aigen.shared.util.JsonUtils;
import dev.langchain4j.model.chat.ChatModel;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;

import java.util.ArrayList;
import java.util.List;

/**
 * Spring Boot auto-configuration for the shared AI infrastructure.
 *
 * <p>This configuration is independent of the article and pregunta auto-configurations and
 * registers everything those bounded contexts need on the AI side:
 *
 * <ul>
 *   <li>An {@link ObjectMapper} (when none has been declared by the consumer).</li>
 *   <li>A {@link JsonUtils} bean for tolerant JSON extraction / parsing.</li>
 *   <li>One per-provider {@link io.github.aigen.shared.ai.infrastructure.AiProviderClient}
 *       (LangChain4j when a {@link ChatModel} bean is available, plus the OpenAI / Gemini /
 *       Ollama REST fall-backs).</li>
 *   <li>A {@link CompositeAiClient} that picks the right strategy at call time.</li>
 *   <li>A {@link RetryingAiPort} decorator that wraps the composite client with exponential
 *       back-off retries, registered as the public {@link AiPort} bean.</li>
 * </ul>
 *
 * <p>Every bean uses {@code @ConditionalOnMissingBean} so the consuming application can
 * override any layer (provider client, composite, retry decorator, …) by exposing its own
 * bean of the same type.
 */
@AutoConfiguration
@EnableConfigurationProperties(ArticleGeneratorProperties.class)
public class AiAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public ObjectMapper articleGeneratorObjectMapper() {
        return new ObjectMapper();
    }

    @Bean
    @ConditionalOnMissingBean
    public JsonUtils jsonUtils(ObjectMapper objectMapper) {
        return new JsonUtils(objectMapper);
    }

    /**
     * LangChain4j strategy bean.  Only registered when a {@link ChatModel} bean is available
     * — otherwise the bean returned is {@code null} and the composite skips it.
     */
    @Bean
    @ConditionalOnMissingBean
    public LangChain4jClient langChain4jClient(ObjectProvider<ChatModel> chatModelProvider) {
        ChatModel chatModel = chatModelProvider.getIfAvailable();
        return new LangChain4jClient(chatModel);
    }

    @Bean
    @ConditionalOnMissingBean
    public OpenAiRestClient openAiRestClient(ArticleGeneratorProperties properties,
                                             ObjectMapper objectMapper) {
        return new OpenAiRestClient((AiConfig) properties, objectMapper);
    }

    @Bean
    @ConditionalOnMissingBean
    public GeminiRestClient geminiRestClient(ArticleGeneratorProperties properties,
                                             ObjectMapper objectMapper) {
        return new GeminiRestClient((AiConfig) properties, objectMapper);
    }

    @Bean
    @ConditionalOnMissingBean
    public OllamaRestClient ollamaRestClient(ArticleGeneratorProperties properties,
                                             ObjectMapper objectMapper) {
        return new OllamaRestClient((AiConfig) properties, objectMapper);
    }

    /**
     * Composite client that selects the appropriate strategy per call.
     *
     * <p>The order of the list defines priority — {@link LangChain4jClient} comes first so it
     * "wins" for every provider whenever a {@link ChatModel} is available.
     */
    @Bean
    @ConditionalOnMissingBean(CompositeAiClient.class)
    public CompositeAiClient compositeAiClient(ArticleGeneratorProperties properties,
                                                LangChain4jClient langChain4jClient,
                                                OpenAiRestClient openAiRestClient,
                                                GeminiRestClient geminiRestClient,
                                                OllamaRestClient ollamaRestClient) {
        List<io.github.aigen.shared.ai.infrastructure.AiProviderClient> clients
                = new ArrayList<>();
        clients.add(langChain4jClient);
        clients.add(openAiRestClient);
        clients.add(geminiRestClient);
        clients.add(ollamaRestClient);
        return new CompositeAiClient(properties, clients);
    }

    /**
     * Public {@link AiPort} bean wrapped with retry logic.  Application services depend on this
     * port — they don't see the per-provider strategies or the retry decorator.
     */
    @Bean
    @ConditionalOnMissingBean(AiPort.class)
    public AiPort aiPort(CompositeAiClient compositeAiClient,
                         ArticleGeneratorProperties properties) {
        return new RetryingAiPort(compositeAiClient, (RetryConfig) properties);
    }
}
