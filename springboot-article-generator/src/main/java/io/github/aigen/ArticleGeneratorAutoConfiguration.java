package io.github.aigen;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.article.application.ArticleAssembler;
import io.github.aigen.article.application.ArticleGeneratorService;
import io.github.aigen.article.application.PromptBuilderService;
import io.github.aigen.article.application.SeoService;
import io.github.aigen.article.application.TextUtils;
import io.github.aigen.article.infrastructure.persistence.JsonFileArticleRepository;
import io.github.aigen.article.infrastructure.persistence.NoopArticleRepository;
import io.github.aigen.article.port.in.ArticleGeneratorPort;
import io.github.aigen.article.port.out.ArticleRepositoryPort;
import io.github.aigen.shared.ai.port.AiPort;
import io.github.aigen.shared.config.ArticleGeneratorProperties;
import io.github.aigen.shared.util.JsonUtils;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;

import java.nio.file.Path;

/**
 * Spring Boot auto-configuration for the article bounded context.
 *
 * <p>Builds on top of {@link AiAutoConfiguration}: the AI-related beans
 * ({@link AiPort}, {@link JsonUtils}, …) are produced there and consumed here.  This class
 * focuses on the article-specific application services, the {@link ArticleAssembler}
 * collaborator and the {@link ArticleRepositoryPort} adapter.
 *
 * <p>Question generation ({@code PreguntaGeneratorService}) is handled separately by
 * {@link PreguntaGeneratorAutoConfiguration}.
 *
 * <p>Activated automatically via
 * {@code META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports}.
 */
@AutoConfiguration(after = AiAutoConfiguration.class)
@EnableConfigurationProperties(ArticleGeneratorProperties.class)
public class ArticleGeneratorAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public TextUtils textUtils() {
        return new TextUtils();
    }

    @Bean
    @ConditionalOnMissingBean
    public SeoService seoService(ArticleGeneratorProperties properties) {
        return new SeoService(properties);
    }

    @Bean
    @ConditionalOnMissingBean
    public PromptBuilderService promptBuilderService(ArticleGeneratorProperties properties) {
        return new PromptBuilderService(properties);
    }

    @Bean
    @ConditionalOnMissingBean
    public ArticleAssembler articleAssembler(ArticleGeneratorProperties properties,
                                             SeoService seoService,
                                             TextUtils textUtils) {
        return new ArticleAssembler(properties, seoService, textUtils);
    }

    /**
     * JSON-file repository, registered when {@code article-generator.output-dir} is
     * configured (and no other {@link ArticleRepositoryPort} bean has been provided).
     */
    @Bean
    @ConditionalOnMissingBean(ArticleRepositoryPort.class)
    @ConditionalOnProperty(prefix = "article-generator", name = "output-dir")
    public ArticleRepositoryPort jsonFileArticleRepository(ArticleGeneratorProperties properties,
                                                            ObjectMapper objectMapper) {
        return new JsonFileArticleRepository(Path.of(properties.getOutputDir()), objectMapper);
    }

    /**
     * No-op fall-back repository used when {@code article-generator.output-dir} is not set.
     */
    @Bean
    @ConditionalOnMissingBean(ArticleRepositoryPort.class)
    public ArticleRepositoryPort noopArticleRepository() {
        return new NoopArticleRepository();
    }

    @Bean
    @ConditionalOnMissingBean(ArticleGeneratorPort.class)
    public ArticleGeneratorService articleGeneratorService(
            ArticleGeneratorProperties properties,
            AiPort aiPort,
            PromptBuilderService promptBuilderService,
            TextUtils textUtils,
            JsonUtils jsonUtils,
            ArticleAssembler articleAssembler,
            ArticleRepositoryPort articleRepository) {
        return new ArticleGeneratorService(
                properties, aiPort, promptBuilderService,
                textUtils, jsonUtils, articleAssembler, articleRepository);
    }
}
