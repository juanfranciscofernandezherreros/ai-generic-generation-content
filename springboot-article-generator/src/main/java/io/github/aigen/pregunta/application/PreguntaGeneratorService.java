package io.github.aigen.pregunta.application;

import com.fasterxml.jackson.databind.JsonNode;
import io.github.aigen.pregunta.config.PreguntaGeneratorProperties;
import io.github.aigen.pregunta.domain.Pregunta;
import io.github.aigen.pregunta.port.in.PreguntaGeneratorPort;
import io.github.aigen.pregunta.port.out.PreguntaRepositoryPort;
import io.github.aigen.shared.ai.port.AiPort;
import io.github.aigen.shared.util.JsonUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Application service that implements the {@link PreguntaGeneratorPort} use case.
 *
 * <p>Reads all existing questions from the {@code preguntas} table via
 * {@link PreguntaRepositoryPort}, asks the configured AI provider via {@link AiPort} for a
 * new unique multilingual question, and persists it.
 *
 * <p>System message and prompt templates can be overridden via
 * {@link PreguntaGeneratorProperties}.
 */
public class PreguntaGeneratorService implements PreguntaGeneratorPort {

    private static final Logger log = LoggerFactory.getLogger(PreguntaGeneratorService.class);

    private final AiPort aiPort;
    private final JsonUtils jsonUtils;
    private final PreguntaRepositoryPort preguntaRepository;
    private final PreguntaGeneratorProperties properties;

    public PreguntaGeneratorService(AiPort aiPort,
                                    PreguntaRepositoryPort preguntaRepository,
                                    JsonUtils jsonUtils,
                                    PreguntaGeneratorProperties properties) {
        this.aiPort = aiPort;
        this.jsonUtils = jsonUtils;
        this.preguntaRepository = preguntaRepository;
        this.properties = properties;
    }

    // ── PreguntaGeneratorPort implementation ──────────────────────────────

    /**
     * {@inheritDoc}
     */
    @Override
    public Pregunta generateAndSave() {
        List<Pregunta> existing = preguntaRepository.findAllByOrderByOrdenAsc();
        log.info("Generating new question. Existing questions in DB: {}", existing.size());

        String prompt = buildPrompt(existing);

        String rawResponse = aiPort.generate(
                properties.getSystemMsg(),
                prompt,
                properties.getMaxTokens(),
                properties.getTemperature());
        String jsonBlock = jsonUtils.extractJsonBlock(rawResponse);
        JsonNode data    = jsonUtils.safeJsonParse(jsonBlock);

        String campo = textNode(data, "campo");
        if (campo.isBlank()) {
            throw new RuntimeException(
                    "AI response is missing the 'campo' field. Raw response preview: "
                    + preview(rawResponse));
        }

        JsonNode textoNode = data.path("texto");
        if (textoNode.isMissingNode() || !textoNode.isObject()) {
            throw new RuntimeException(
                    "AI response is missing the 'texto' object. Raw response preview: "
                    + preview(rawResponse));
        }

        Map<String, String> texto = new LinkedHashMap<>();
        for (String lang : properties.getLanguages()) {
            String val = textoNode.path(lang).asText("").strip();
            if (val.isBlank()) {
                throw new RuntimeException(
                        "AI response is missing the '" + lang + "' translation in 'texto'. "
                        + "Raw response preview: " + preview(rawResponse));
            }
            texto.put(lang, val);
        }

        if (preguntaRepository.existsByCampo(campo)) {
            throw new RuntimeException(
                    "AI generated a 'campo' that already exists in the database: \"" + campo + "\"");
        }

        String generatedEs = texto.get("es");
        if (generatedEs != null) {
            boolean textDuplicate = existing.stream()
                    .map(p -> p.getTexto() != null ? p.getTexto().get("es") : null)
                    .filter(t -> t != null)
                    .anyMatch(t -> t.equalsIgnoreCase(generatedEs));
            if (textDuplicate) {
                throw new RuntimeException(
                        "AI generated a Spanish question text that already exists: \"" + generatedEs + "\"");
            }
        }

        int nextOrden = existing.stream()
                .map(Pregunta::getOrden)
                .filter(o -> o != null)
                .max(Integer::compareTo)
                .map(max -> max + 1)
                .orElse(1);

        Pregunta nueva = new Pregunta(campo, nextOrden, texto);
        Pregunta saved = preguntaRepository.save(nueva);
        log.info("New question saved: id={}, campo='{}', orden={}, es='{}'",
                saved.getId(), saved.getCampo(), saved.getOrden(), texto.get("es"));
        return saved;
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    private String buildPrompt(List<Pregunta> existing) {
        if (existing.isEmpty()) {
            return properties.getEmptyPrompt();
        }

        StringBuilder bullets = new StringBuilder();
        existing.stream()
                .limit(properties.getMaxContextQuestions())
                .forEach(p -> {
                    String es = p.getTexto() != null ? p.getTexto().get("es") : "";
                    bullets.append("- ").append(p.getCampo()).append(": ").append(es).append("\n");
                });
        return properties.getExistingPromptTemplate().replace("{existing}", bullets.toString());
    }

    private static String preview(String text) {
        if (text == null) return "";
        return text.substring(0, Math.min(300, text.length()));
    }

    private static String textNode(JsonNode node, String field) {
        JsonNode n = node.path(field);
        return n.isMissingNode() || n.isNull() ? "" : n.asText("").strip();
    }
}
