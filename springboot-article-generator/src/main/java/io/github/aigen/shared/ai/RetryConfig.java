package io.github.aigen.shared.ai;

/**
 * Narrow read-only view of the retry-related configuration.
 *
 * <p>Used by {@code RetryingAiPort} so the retry policy can be tuned without exposing the
 * whole {@code ArticleGeneratorProperties} bag.
 */
public interface RetryConfig {

    /** Maximum retries for a transient failure (must be ≥ 1). */
    int getMaxApiRetries();

    /** Base delay (in seconds) for the exponential back-off. */
    int getRetryBaseDelaySeconds();
}
