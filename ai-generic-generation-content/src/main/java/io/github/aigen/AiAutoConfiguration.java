package io.github.aigen;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.article.config.ArticleGeneratorProperties;
import io.github.aigen.shared.ai.port.AiPort;
import io.github.aigen.shared.ai.infrastructure.*;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.*;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Collections;
import java.util.List;

@AutoConfiguration
@EnableConfigurationProperties(ArticleGeneratorProperties.class)
public class AiAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public ObjectMapper objectMapper() {
        return new ObjectMapper();
    }

    // ---------------- CONFIGURACIÓN PARA OPENAI ----------------
    @Configuration
    @ConditionalOnProperty(name = "ai.provider", havingValue = "openai")
    static class OpenAiConfiguration {
        @Bean
        @ConditionalOnMissingBean
        public OpenAiRestClient openAiClient(ObjectMapper mapper, ArticleGeneratorProperties props) {
            return new OpenAiRestClient(props, mapper);
        }
    }

    // ---------------- CONFIGURACIÓN PARA GEMINI ----------------
    @Configuration
    @ConditionalOnProperty(name = "ai.provider", havingValue = "gemini")
    static class GeminiConfiguration {
        @Bean
        @ConditionalOnMissingBean
        public GeminiRestClient geminiClient(ObjectMapper mapper, ArticleGeneratorProperties props) {
            return new GeminiRestClient(props, mapper);
        }
    }

    // ---------------- CONFIGURACIÓN PARA OLLAMA ----------------
    @Configuration
    @ConditionalOnProperty(name = "ai.provider", havingValue = "ollama")
    static class OllamaConfiguration {
        @Bean
        @ConditionalOnMissingBean
        public OllamaRestClient ollamaClient(ObjectMapper mapper, ArticleGeneratorProperties props) {
            return new OllamaRestClient(props, mapper);
        }
    }

    @Bean
    @ConditionalOnMissingBean
    public CompositeAiClient compositeAiClient(
            ArticleGeneratorProperties props,
            List<AiProviderClient> availableClients // Spring inyectará solo los que se hayan creado arriba
    ) {
        // Si no hay clientes activos por propiedad, lanzamos error claro
        if (availableClients.isEmpty()) {
            throw new IllegalStateException("No AI client bean was created. Check 'ai.provider' property.");
        }
        return new CompositeAiClient(props, availableClients);
    }

    @Bean
    @ConditionalOnMissingBean(AiPort.class)
    public AiPort aiPort(CompositeAiClient composite, ArticleGeneratorProperties props) {
        return new RetryingAiPort(composite, props);
    }
}