package com.github.juanfernandez.article.article.infrastructure.persistence;

import com.github.juanfernandez.article.article.domain.Article;
import com.github.juanfernandez.article.article.port.out.ArticleRepositoryPort;

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
