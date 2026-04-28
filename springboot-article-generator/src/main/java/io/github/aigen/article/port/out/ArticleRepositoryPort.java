package io.github.aigen.article.port.out;

import io.github.aigen.article.domain.Article;

/**
 * Secondary (output) port for article persistence.
 *
 * <p>Decouples the {@code ArticleGeneratorService} application service from any specific
 * persistence technology.  The default Spring auto-configuration registers a no-op adapter
 * that returns the article unchanged — opt-in adapters (file system, database, …) replace
 * it when configured.
 *
 * <p>Available built-in adapters:
 * <ul>
 *   <li>{@code NoopArticleRepository} — default; performs no I/O.</li>
 *   <li>{@code JsonFileArticleRepository} — writes the article as a {@code .json} file when
 *       {@code article-generator.output-dir} is configured.</li>
 * </ul>
 */
public interface ArticleRepositoryPort {

    /**
     * Persists the {@code article} (or skips persistence when the adapter is a no-op) and
     * returns it back so the use-case can chain calls.
     *
     * @param article the freshly assembled article
     * @return the same {@link Article} instance (or a new one with adapter-supplied fields,
     *         e.g. database identifiers)
     */
    Article save(Article article);
}
