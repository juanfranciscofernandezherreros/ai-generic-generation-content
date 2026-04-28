package io.github.aigen.shared.ai.infrastructure;

import io.github.aigen.shared.ai.RetryConfig;
import io.github.aigen.shared.ai.port.AiPort;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Random;

/**
 * Decorator that adds exponential-back-off retries to any {@link AiPort}.
 *
 * <p>Only retries <em>transient</em> network errors — connection refused, unknown host,
 * connect/read timeouts.  Permanent errors (4xx, parse errors, …) propagate immediately.
 *
 * <p>The base delay grows exponentially with the attempt number plus a small random jitter
 * to avoid thundering-herd behaviour:
 * <pre>{@code wait = baseDelay * 2^(attempt-1) + random(0,1) seconds}</pre>
 */
public class RetryingAiPort implements AiPort {

    private static final Logger log = LoggerFactory.getLogger(RetryingAiPort.class);
    private static final Random RANDOM = new Random();

    private final AiPort delegate;
    private final RetryConfig retryConfig;

    public RetryingAiPort(AiPort delegate, RetryConfig retryConfig) {
        this.delegate = delegate;
        this.retryConfig = retryConfig;
    }

    @Override
    public String generate(String systemMsg, String userPrompt, int maxTokens, double temperature) {
        int maxRetries = Math.max(1, retryConfig.getMaxApiRetries());
        int baseDelay  = Math.max(0, retryConfig.getRetryBaseDelaySeconds());
        RuntimeException lastException = null;

        for (int attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return delegate.generate(systemMsg, userPrompt, maxTokens, temperature);
            } catch (RuntimeException e) {
                if (!isTransientError(e)) {
                    throw e;
                }
                lastException = e;
                if (attempt == maxRetries) break;
                double wait = baseDelay * Math.pow(2, attempt - 1) + RANDOM.nextDouble();
                log.warn("Transient AI error on attempt {}/{}: {}. Retrying in {}s.",
                        attempt, maxRetries, e.getMessage(), String.format("%.1f", wait));
                try {
                    Thread.sleep((long) (wait * 1000));
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    throw new RuntimeException("Interrupted during retry wait", ie);
                }
            }
        }
        throw new RuntimeException("AI API failed after " + maxRetries + " retries", lastException);
    }

    /** Visible for testing. */
    static boolean isTransientError(Throwable error) {
        Throwable cause = error.getCause() != null ? error.getCause() : error;
        String msg = cause.getClass().getName() + " " + (cause.getMessage() != null ? cause.getMessage() : "");
        return msg.contains("ConnectException")
                || msg.contains("SocketTimeoutException")
                || msg.contains("ConnectionRefused")
                || msg.contains("UnknownHostException");
    }
}
