package io.github.aigen;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.shared.config.ArticleGeneratorProperties;
import io.github.aigen.shared.ai.port.AiPort;
import io.github.aigen.shared.ai.infrastructure.*;
import io.github.aigen.shared.ai.RetryConfig;
import dev.langchain4j.model.chat.ChatModel;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;

import java.util.ArrayList;
import java.util.List;

@AutoConfiguration
@EnableConfigurationProperties(ArticleGeneratorProperties.class)
public class AiAutoConfiguration {

    // ---------------- JSON ----------------

    @Bean
    @ConditionalOnMissingBean
    public ObjectMapper objectMapper() {
        return new ObjectMapper();
    }

    // ---------------- PROVIDERS ----------------

    @Bean
    @ConditionalOnBean(ChatModel.class)
    public LangChain4jClient langChain4jClient(ChatModel chatModel) {
        return new LangChain4jClient(chatModel);
    }

    @Bean
    @ConditionalOnMissingBean
    public OpenAiRestClient openAiClient(ObjectMapper mapper,
                                         ArticleGeneratorProperties props) {
        return new OpenAiRestClient(props, mapper);
    }

    @Bean
    @ConditionalOnMissingBean
    public GeminiRestClient geminiClient(ObjectMapper mapper,
                                         ArticleGeneratorProperties props) {
        return new GeminiRestClient(props, mapper);
    }

    @Bean
    @ConditionalOnMissingBean
    public OllamaRestClient ollamaClient(ObjectMapper mapper,
                                         ArticleGeneratorProperties props) {
        return new OllamaRestClient(props, mapper);
    }

    // ---------------- COMPOSITE (SELECCIÓN POR CONFIG) ----------------

    @Bean
    @ConditionalOnMissingBean
    public CompositeAiClient compositeAiClient(
            ArticleGeneratorProperties props,
            ObjectProvider<LangChain4jClient> langChain4j,
            ObjectProvider<OpenAiRestClient> openAi,
            ObjectProvider<GeminiRestClient> gemini,
            ObjectProvider<OllamaRestClient> ollama
    ) {

        List<AiProviderClient> clients = new ArrayList<>();

        switch (props.getProvider().toString().toLowerCase()) {

            case "langchain" -> langChain4j.ifAvailable(clients::add);

            case "openai" -> openAi.ifAvailable(clients::add);

            case "gemini" -> gemini.ifAvailable(clients::add);

            case "ollama" -> ollama.ifAvailable(clients::add);

            default -> throw new IllegalArgumentException(
                    "Unknown provider: " + props.getProvider()
            );
        }

        return new CompositeAiClient(props, clients);
    }

    // ---------------- PORT ----------------

    @Bean
    @ConditionalOnMissingBean(AiPort.class)
    public AiPort aiPort(CompositeAiClient composite,
                         ArticleGeneratorProperties props) {

        return new RetryingAiPort(composite, props);
    }
}