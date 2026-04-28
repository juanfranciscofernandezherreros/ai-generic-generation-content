package io.github.aigen.article.infrastructure.persistence;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.article.domain.Article;
import io.github.aigen.article.port.out.ArticleRepositoryPort;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * {@link ArticleRepositoryPort} adapter that serialises the article to a JSON file inside a
 * configurable output directory.
 *
 * <p>Activated by setting {@code article-generator.output-dir} in
 * {@code application.properties}/{@code yml}.  The file name is derived from the article
 * slug ({@code <slug>.json}); the directory is created lazily on first save.
 */
public class JsonFileArticleRepository implements ArticleRepositoryPort {

    private static final Logger log = LoggerFactory.getLogger(JsonFileArticleRepository.class);

    private final Path outputDir;
    private final ObjectMapper objectMapper;

    public JsonFileArticleRepository(Path outputDir, ObjectMapper objectMapper) {
        this.outputDir = outputDir;
        this.objectMapper = objectMapper;
    }

    @Override
    public Article save(Article article) {
        if (article == null) {
            throw new IllegalArgumentException("Article must not be null");
        }
        String slug = article.getSlug();
        if (slug == null || slug.isBlank()) {
            throw new IllegalStateException(
                    "Article slug must not be blank — cannot derive output filename");
        }

        try {
            Files.createDirectories(outputDir);
            Path target = outputDir.resolve(safeFileName(slug) + ".json");
            byte[] payload = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsBytes(article);
            Files.write(target, payload);
            log.info("Article persisted to {}", target);
        } catch (IOException e) {
            throw new RuntimeException(
                    "Failed to write article to " + outputDir + ": " + e.getMessage(), e);
        }
        return article;
    }

    /**
     * Strips path separators and parent-directory traversal sequences from {@code slug}.
     * Slugs are already lowercase alphanumeric + dash, but defending in depth in case a
     * caller bypasses {@code TextUtils.slugify}.
     */
    static String safeFileName(String slug) {
        return slug.replace("/", "-")
                   .replace("\\", "-")
                   .replace("..", "-");
    }
}
