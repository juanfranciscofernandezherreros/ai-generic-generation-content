package io.github.aigen.pregunta.application;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.aigen.pregunta.config.PreguntaGeneratorProperties;
import io.github.aigen.pregunta.domain.Pregunta;
import io.github.aigen.pregunta.port.out.PreguntaRepositoryPort;
import io.github.aigen.shared.ai.port.AiPort;
import io.github.aigen.shared.util.JsonUtils;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link PreguntaGeneratorService} verifying behaviour around the externalised
 * prompt templates and validation.
 */
class PreguntaGeneratorServiceTest {

    private PreguntaGeneratorProperties properties;
    private JsonUtils jsonUtils;
    private RecordingRepository repository;

    @BeforeEach
    void setUp() {
        properties = new PreguntaGeneratorProperties();
        jsonUtils = new JsonUtils(new ObjectMapper());
        repository = new RecordingRepository();
    }

    private PreguntaGeneratorService service(String aiResponse, AtomicReference<String> capturedPrompt) {
        AiPort fakeAi = (sys, prompt, maxTokens, temp) -> {
            capturedPrompt.set(prompt);
            return aiResponse;
        };
        return new PreguntaGeneratorService(fakeAi, repository, jsonUtils, properties);
    }

    @Test
    void usesEmptyPromptWhenRepositoryIsEmpty() {
        AtomicReference<String> captured = new AtomicReference<>();
        String aiJson = "{\"campo\":\"primera\",\"texto\":{\"ca\":\"Q\",\"en\":\"Q\",\"es\":\"Q\",\"fr\":\"Q\"}}";

        Pregunta saved = service(aiJson, captured).generateAndSave();

        assertEquals(properties.getEmptyPrompt(), captured.get());
        assertEquals("primera", saved.getCampo());
        assertEquals(1, saved.getOrden());
    }

    @Test
    void rendersExistingTemplateWithBulletList() {
        repository.preload(new Pregunta("uno", 1, Map.of("es", "Pregunta uno")));
        repository.preload(new Pregunta("dos", 2, Map.of("es", "Pregunta dos")));

        AtomicReference<String> captured = new AtomicReference<>();
        String aiJson = "{\"campo\":\"tres\",\"texto\":{\"ca\":\"Q\",\"en\":\"Q\",\"es\":\"Q\",\"fr\":\"Q\"}}";

        service(aiJson, captured).generateAndSave();

        String prompt = captured.get();
        assertTrue(prompt.contains("- uno: Pregunta uno"), "Prompt should embed first bullet");
        assertTrue(prompt.contains("- dos: Pregunta dos"), "Prompt should embed second bullet");
        assertFalse(prompt.contains("{existing}"),       "Placeholder must be replaced");
    }

    @Test
    void honoursCustomLanguagesList() {
        properties.setLanguages(List.of("es", "en"));
        AtomicReference<String> captured = new AtomicReference<>();
        // No 'ca'/'fr' keys — should still succeed because they're not requested.
        String aiJson = "{\"campo\":\"a\",\"texto\":{\"es\":\"Hola\",\"en\":\"Hi\"}}";

        Pregunta saved = service(aiJson, captured).generateAndSave();
        assertEquals("Hola", saved.getTexto().get("es"));
        assertEquals("Hi",   saved.getTexto().get("en"));
    }

    @Test
    void rejectsResponseMissingARequestedLanguage() {
        AtomicReference<String> captured = new AtomicReference<>();
        // Missing 'fr'
        String aiJson = "{\"campo\":\"a\",\"texto\":{\"ca\":\"Q\",\"en\":\"Q\",\"es\":\"Q\"}}";

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> service(aiJson, captured).generateAndSave());
        assertTrue(ex.getMessage().contains("'fr'"),
                "Expected error to mention missing language, got: " + ex.getMessage());
    }

    @Test
    void rejectsResponseMissingCampo() {
        AtomicReference<String> captured = new AtomicReference<>();
        String aiJson = "{\"texto\":{\"ca\":\"Q\",\"en\":\"Q\",\"es\":\"Q\",\"fr\":\"Q\"}}";

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> service(aiJson, captured).generateAndSave());
        assertTrue(ex.getMessage().contains("campo"));
    }

    @Test
    void rejectsDuplicateCampo() {
        repository.preload(new Pregunta("yaExiste", 1, Map.of("es", "x")));
        repository.markCampoUsed("yaExiste");

        AtomicReference<String> captured = new AtomicReference<>();
        String aiJson = "{\"campo\":\"yaExiste\",\"texto\":{\"ca\":\"Q\",\"en\":\"Q\",\"es\":\"Q\",\"fr\":\"Q\"}}";

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> service(aiJson, captured).generateAndSave());
        assertTrue(ex.getMessage().contains("yaExiste"));
    }

    @Test
    void rejectsDuplicateSpanishText() {
        repository.preload(new Pregunta("uno", 1, Map.of("es", "Repetido")));
        AtomicReference<String> captured = new AtomicReference<>();
        String aiJson = "{\"campo\":\"otro\",\"texto\":{\"ca\":\"x\",\"en\":\"x\",\"es\":\"Repetido\",\"fr\":\"x\"}}";

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> service(aiJson, captured).generateAndSave());
        assertTrue(ex.getMessage().toLowerCase().contains("already exists"));
    }

    @Test
    void respectsMaxContextQuestionsLimit() {
        properties.setMaxContextQuestions(1);
        repository.preload(new Pregunta("a", 1, Map.of("es", "primera")));
        repository.preload(new Pregunta("b", 2, Map.of("es", "segunda")));

        AtomicReference<String> captured = new AtomicReference<>();
        String aiJson = "{\"campo\":\"c\",\"texto\":{\"ca\":\"Q\",\"en\":\"Q\",\"es\":\"Q\",\"fr\":\"Q\"}}";
        service(aiJson, captured).generateAndSave();

        assertTrue(captured.get().contains("- a: primera"));
        assertFalse(captured.get().contains("- b: segunda"),
                "Second question should be truncated by maxContextQuestions=1");
    }

    @Test
    void usesSystemMsgFromProperties() {
        properties.setSystemMsg("CUSTOM-SYSTEM-MSG");
        AtomicReference<String> capturedSystem = new AtomicReference<>();
        AiPort fakeAi = (sys, prompt, maxTokens, temp) -> {
            capturedSystem.set(sys);
            return "{\"campo\":\"x\",\"texto\":{\"ca\":\"a\",\"en\":\"a\",\"es\":\"a\",\"fr\":\"a\"}}";
        };
        new PreguntaGeneratorService(fakeAi, repository, jsonUtils, properties).generateAndSave();
        assertEquals("CUSTOM-SYSTEM-MSG", capturedSystem.get());
    }

    // ── Test double ───────────────────────────────────────────────────────

    private static final class RecordingRepository implements PreguntaRepositoryPort {
        private final java.util.List<Pregunta> data = new java.util.ArrayList<>();
        private final java.util.Set<String> usedCampos = new java.util.HashSet<>();

        void preload(Pregunta p) {
            if (p.getId() == null) p.setId(UUID.randomUUID());
            data.add(p);
        }

        void markCampoUsed(String campo) { usedCampos.add(campo); }

        @Override public List<Pregunta> findAllByOrderByOrdenAsc() {
            return data.stream()
                    .sorted((a, b) -> Integer.compare(a.getOrden(), b.getOrden()))
                    .toList();
        }
        @Override public Pregunta save(Pregunta p) {
            if (p.getId() == null) p.setId(UUID.randomUUID());
            data.add(p);
            return p;
        }
        @Override public boolean existsByCampo(String campo) { return usedCampos.contains(campo); }
        @Override public List<Map<String, String>> findAllTextos() {
            return data.stream().map(Pregunta::getTexto).toList();
        }
    }
}
