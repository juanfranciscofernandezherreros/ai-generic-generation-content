package io.github.aigen.article.infrastructure.persistence;

import io.github.aigen.article.domain.Article;
import io.github.aigen.article.port.out.ArticleRepositoryPort;

/**
 * Default {@link ArticleRepositoryPort} adapter that performs no I/O.
 *
 * <p>Keeps the {@code ArticleGeneratorService} contract simple: it always calls
 * {@code repository.save(article)} regardless of whether the consuming application has
 * opted into a persistence adapter.
 */
public class NoopArticleRepository implements ArticleRepositoryPort {

    @Override
    public Article save(Article article) {
        return article;
    }
}
