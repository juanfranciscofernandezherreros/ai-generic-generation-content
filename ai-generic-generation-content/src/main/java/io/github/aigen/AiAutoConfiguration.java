package io.github.aigen;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.article.config.ArticleGeneratorProperties;
import io.github.aigen.shared.ai.port.AiPort;
import io.github.aigen.shared.ai.infrastructure.*;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.beans.factory.ObjectProvider;
import java.util.List;

@AutoConfiguration
public class AiAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public ObjectMapper objectMapper() {
        return new ObjectMapper();
    }

    // --- AISLAMIENTO TOTAL DE LANGCHAIN4J ---
    @Configuration
    // El secreto: Usar el nombre como String para que la JVM no busque la clase al cargar el archivo
    @ConditionalOnClass(name = "dev.langchain4j.model.chat.ChatModel")
    @ConditionalOnProperty(name = "ai.provider", havingValue = "langchain")
    static class LangChainConfig {
        @Bean
        public LangChain4jClient langChain4jClient(ObjectProvider<dev.langchain4j.model.chat.ChatModel> modelProvider) {
            return new LangChain4jClient(modelProvider.getIfAvailable());
        }
    }

    @Bean
    @ConditionalOnProperty(name = "ai.provider", havingValue = "openai")
    public OpenAiRestClient openAiClient(ObjectMapper mapper, ArticleGeneratorProperties props) {
        return new OpenAiRestClient(props, mapper);
    }

    @Bean
    @ConditionalOnProperty(name = "ai.provider", havingValue = "gemini")
    public GeminiRestClient geminiClient(ObjectMapper mapper, ArticleGeneratorProperties props) {
        return new GeminiRestClient(props, mapper);
    }

    @Bean
    @ConditionalOnProperty(name = "ai.provider", havingValue = "ollama")
    public OllamaRestClient ollamaClient(ObjectMapper mapper, ArticleGeneratorProperties props) {
        return new OllamaRestClient(props, mapper);
    }

    @Bean
    @ConditionalOnMissingBean(AiPort.class)
    public AiPort aiPort(List<AiProviderClient> clients, ArticleGeneratorProperties props) {
        if (clients.isEmpty()) {
            throw new IllegalStateException("Debes configurar 'ai.provider' en el yml (gemini, openai, etc)");
        }
        // Tomamos el primer cliente de la lista (el único que se habrá creado por propiedad)
        return new RetryingAiPort(new CompositeAiClient(props, clients), props);
    }
}