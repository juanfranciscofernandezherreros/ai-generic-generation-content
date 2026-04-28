package io.github.aigen.article.port.in;

import io.github.aigen.article.domain.Article;
import io.github.aigen.article.domain.ArticleRequest;

/**
 * Primary (input) port for the article bounded context.
 *
 * <p>Defines the use case exposed to the outside world: generate a complete SEO article
 * from an {@link ArticleRequest}.  The concrete implementation lives in the application layer
 * ({@code ArticleGeneratorService}).
 *
 * <p>Consumers of the library can inject this interface directly to remain decoupled from the
 * implementation class.
 */
public interface ArticleGeneratorPort {

    /**
     * Generates a complete SEO article from an {@link ArticleRequest}.
     *
     * <p>Per-request fields ({@code authorUsername}, {@code site}, {@code language}) override the
     * corresponding values from the configuration properties when non-null.
     *
     * @param request article generation parameters
     * @return fully populated {@link Article} with SEO metadata
     * @throws IllegalArgumentException if {@code request.category} is blank
     * @throws RuntimeException         if the AI fails to generate a unique title after all retries
     */
    Article generateArticle(ArticleRequest request);
}
