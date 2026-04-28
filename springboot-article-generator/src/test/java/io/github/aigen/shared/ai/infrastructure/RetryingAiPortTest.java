package io.github.aigen.shared.ai.infrastructure;

import io.github.aigen.shared.ai.RetryConfig;
import io.github.aigen.shared.ai.port.AiPort;
import org.junit.jupiter.api.Test;

import java.net.ConnectException;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for {@link RetryingAiPort}.
 */
class RetryingAiPortTest {

    private static final RetryConfig FAST_RETRY = new RetryConfig() {
        @Override public int getMaxApiRetries() { return 3; }
        // Zero delay so the test runs in milliseconds.
        @Override public int getRetryBaseDelaySeconds() { return 0; }
    };

    @Test
    void returnsImmediatelyOnSuccess() {
        AiPort delegate = (sys, prompt, maxTokens, temp) -> "OK";
        String result = new RetryingAiPort(delegate, FAST_RETRY).generate("s", "u", 1, 0);
        assertEquals("OK", result);
    }

    @Test
    void doesNotRetryPermanentErrors() {
        AtomicInteger calls = new AtomicInteger();
        AiPort delegate = (sys, prompt, maxTokens, temp) -> {
            calls.incrementAndGet();
            throw new RuntimeException("400 Bad Request");
        };
        assertThrows(RuntimeException.class,
                () -> new RetryingAiPort(delegate, FAST_RETRY).generate("s", "u", 1, 0));
        assertEquals(1, calls.get(), "Permanent errors must not be retried.");
    }

    @Test
    void retriesTransientErrorsAndEventuallySucceeds() {
        AtomicInteger calls = new AtomicInteger();
        AiPort delegate = (sys, prompt, maxTokens, temp) -> {
            int call = calls.incrementAndGet();
            if (call < 3) {
                throw new RuntimeException("net failure", new ConnectException("Connection refused"));
            }
            return "recovered";
        };
        String result = new RetryingAiPort(delegate, FAST_RETRY).generate("s", "u", 1, 0);
        assertEquals("recovered", result);
        assertEquals(3, calls.get());
    }

    @Test
    void givesUpAfterMaxRetriesOnPersistentTransientErrors() {
        AtomicInteger calls = new AtomicInteger();
        AiPort delegate = (sys, prompt, maxTokens, temp) -> {
            calls.incrementAndGet();
            throw new RuntimeException("net failure", new ConnectException("Connection refused"));
        };
        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> new RetryingAiPort(delegate, FAST_RETRY).generate("s", "u", 1, 0));
        assertEquals(3, calls.get());
        assertTrue(ex.getMessage().contains("after 3 retries"),
                "Expected exhaustion message, got: " + ex.getMessage());
    }

    @Test
    void detectsTransientErrorsByCauseClassName() {
        assertTrue(RetryingAiPort.isTransientError(
                new RuntimeException("wrap", new ConnectException("refused"))));
        assertFalse(RetryingAiPort.isTransientError(
                new RuntimeException("plain bad input")));
    }
}
