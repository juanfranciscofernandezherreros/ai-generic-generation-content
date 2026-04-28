package io.github.aigen.shared.ai.infrastructure;

import io.github.aigen.shared.ai.AiConfig;
import io.github.aigen.shared.ai.AiProvider;
import io.github.aigen.shared.ai.port.AiPort;

import java.util.List;

/**
 * Composite {@link AiPort} that selects the appropriate {@link AiProviderClient}
 * for each call.
 *
 * <p>Behaviour:
 * <ol>
 *   <li>Resolve the effective provider with {@link AiProviderResolver#resolve(AiConfig)}.</li>
 *   <li>Iterate over the registered {@link AiProviderClient}s — the <strong>first</strong> one
 *       whose {@link AiProviderClient#supports(AiProvider, AiConfig)} returns {@code true} wins.</li>
 *   <li>If none matches, throw a descriptive {@link RuntimeException}.</li>
 * </ol>
 *
 * <p>The order of the list matters.  Spring's auto-configuration registers the
 * {@link LangChain4jClient} first when a {@code ChatModel} bean is available, so it acts as
 * an "all-providers wins" route, while the REST clients are the fallback for
 * back-ends that don't require LangChain4j.
 */
public class CompositeAiClient implements AiPort {

    private final AiConfig config;
    private final List<AiProviderClient> clients;

    public CompositeAiClient(AiConfig config, List<AiProviderClient> clients) {
        this.config = config;
        this.clients = List.copyOf(clients);
    }

    @Override
    public String generate(String systemMsg, String userPrompt, int maxTokens, double temperature) {
        AiProvider resolved = AiProviderResolver.resolve(config);

        for (AiProviderClient client : clients) {
            if (client.supports(resolved, config)) {
                return client.generate(systemMsg, userPrompt, maxTokens, temperature);
            }
        }

        if (resolved == AiProvider.ANTHROPIC) {
            throw new RuntimeException(
                    "Anthropic provider requires LangChain4j. "
                    + "Add langchain4j-anthropic-spring-boot-starter and configure "
                    + "langchain4j.anthropic.chat-model.api-key in application.yml.");
        }

        throw new RuntimeException(
                "No AiProviderClient registered for provider " + resolved
                + ". Configure a LangChain4j ChatModel bean or one of the REST adapters.");
    }
}
