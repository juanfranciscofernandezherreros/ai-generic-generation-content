package com.github.juanfernandez.article.service;

import com.github.juanfernandez.article.model.Pregunta;
import com.github.juanfernandez.article.repository.PreguntaRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.stream.Collectors;

/**
 * Service that reads all existing questions from the {@code preguntas} PostgreSQL table,
 * uses the configured AI provider to generate a new unique question, and then persists it.
 *
 * <p>Example usage from a consuming Spring Boot application:
 * <pre>{@code
 * @Autowired
 * private PreguntaGeneratorService preguntaGeneratorService;
 *
 * // Generate and save a new question in a specific category
 * Pregunta nueva = preguntaGeneratorService.generateAndSave("Spring Boot");
 *
 * // Generate and save a question without a category
 * Pregunta nueva = preguntaGeneratorService.generateAndSave(null);
 * }</pre>
 *
 * <p>This bean is only registered when both {@code spring-boot-starter-data-jpa}
 * and a {@link PreguntaRepository} are on the classpath (conditional on
 * {@code @ConditionalOnBean(PreguntaRepository.class)} in the auto-configuration).
 */
public class PreguntaGeneratorService {

    private static final Logger log = LoggerFactory.getLogger(PreguntaGeneratorService.class);

    /** Maximum number of existing questions included in the AI prompt to avoid exceeding token limits. */
    private static final int MAX_CONTEXT_QUESTIONS = 100;

    private static final String SYSTEM_MSG =
            "Eres un experto generador de preguntas técnicas y educativas. "
            + "Tu tarea es crear una pregunta nueva, clara y útil que no exista ya en la lista proporcionada. "
            + "Devuelve ÚNICAMENTE el texto de la pregunta, sin numeración, sin comillas ni explicación adicional.";

    private final AiClientService aiClient;
    private final PreguntaRepository preguntaRepository;

    public PreguntaGeneratorService(AiClientService aiClient,
                                    PreguntaRepository preguntaRepository) {
        this.aiClient            = aiClient;
        this.preguntaRepository  = preguntaRepository;
    }

    // ── Public API ────────────────────────────────────────────────────────

    /**
     * Fetches all questions from the database, asks the AI to generate a new one that does not
     * already exist, saves it, and returns the persisted {@link Pregunta}.
     *
     * @param categoria optional category for the new question; may be {@code null}
     * @return the newly created and persisted {@link Pregunta}
     * @throws RuntimeException if the AI returns an empty question
     * @throws RuntimeException if the AI generates a question that already exists in the database
     */
    public Pregunta generateAndSave(String categoria) {
        List<String> existing = preguntaRepository.findAllPreguntaTexts();
        log.info("Generating new question. Existing questions in DB: {}", existing.size());

        String prompt = buildPrompt(existing, categoria);
        String generated = aiClient.generate(SYSTEM_MSG, prompt, 200, 0.8)
                .strip()
                .replaceAll("^[\"']|[\"']$", "")   // strip wrapping quotes if any
                .strip();

        if (generated.isBlank()) {
            throw new RuntimeException(
                    "AI returned an empty question"
                    + (categoria != null && !categoria.isBlank() ? " for category: " + categoria : "")
                    + ". This may indicate an issue with the AI service or prompt configuration.");
        }

        // Basic deduplication check (case-insensitive exact match)
        boolean duplicate = existing.stream()
                .anyMatch(q -> q.equalsIgnoreCase(generated));
        if (duplicate) {
            throw new RuntimeException(
                    "AI generated a question that already exists in the database: \"" + generated + "\"");
        }

        Pregunta nueva = new Pregunta(generated, categoria);
        Pregunta saved = preguntaRepository.save(nueva);
        log.info("New question saved with id={}: '{}'", saved.getId(), saved.getPregunta());
        return saved;
    }

    /**
     * Convenience overload that generates a question without a specific category.
     *
     * @return the newly created and persisted {@link Pregunta}
     */
    public Pregunta generateAndSave() {
        return generateAndSave(null);
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    private String buildPrompt(List<String> existing, String categoria) {
        StringBuilder sb = new StringBuilder();

        if (categoria != null && !categoria.isBlank()) {
            sb.append("Categoría: ").append(categoria).append("\n\n");
        }

        if (existing.isEmpty()) {
            sb.append("No hay preguntas registradas todavía. Crea la primera pregunta.");
        } else {
            sb.append("Las siguientes preguntas YA EXISTEN. NO puedes repetir ninguna de ellas:\n");
            existing.stream()
                    .limit(MAX_CONTEXT_QUESTIONS)
                    .forEach(q -> sb.append("- ").append(q).append("\n"));
            sb.append("\nGenera UNA NUEVA pregunta que sea diferente a todas las anteriores.");
        }

        return sb.toString();
    }
}
