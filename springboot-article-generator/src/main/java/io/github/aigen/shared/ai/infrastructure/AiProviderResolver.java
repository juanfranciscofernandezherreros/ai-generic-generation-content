package io.github.aigen.shared.ai.infrastructure;

import io.github.aigen.shared.ai.AiConfig;
import io.github.aigen.shared.ai.AiProvider;

/**
 * Resolves the effective {@link AiProvider} from an {@link AiConfig}.
 *
 * <p>When the configuration is set to {@link AiProvider#AUTO} the resolution rules are:
 * <ol>
 *   <li>If the model name starts with {@code gemini-} → {@link AiProvider#GEMINI}.</li>
 *   <li>If {@code ollama-base-url} is configured → {@link AiProvider#OLLAMA}.</li>
 *   <li>Otherwise → {@link AiProvider#OPENAI}.</li>
 * </ol>
 *
 * <p>Any explicit value other than {@code AUTO} is returned unchanged.
 */
public final class AiProviderResolver {

    private AiProviderResolver() {}

    /** Returns the effective provider for {@code config}. */
    public static AiProvider resolve(AiConfig config) {
        AiProvider configured = config.getProvider();
        if (configured != null && configured != AiProvider.AUTO) {
            return configured;
        }
        String model = config.getModel();
        if (model != null && model.toLowerCase().startsWith("gemini")) {
            return AiProvider.GEMINI;
        }
        String baseUrl = config.getOllamaBaseUrl();
        if (baseUrl != null && !baseUrl.isBlank()) {
            return AiProvider.OLLAMA;
        }
        return AiProvider.OPENAI;
    }
}
