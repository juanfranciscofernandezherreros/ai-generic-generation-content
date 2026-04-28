package io.github.aigen.pregunta.port.out;

import io.github.aigen.pregunta.domain.Pregunta;

import java.util.List;
import java.util.Map;

/**
 * Secondary (output) port for pregunta persistence.
 *
 * <p>Decouples the {@code PreguntaGeneratorService} application service from any specific
 * persistence technology.  The infrastructure adapter {@code JpaPreguntaRepository}
 * provides the Spring Data JPA implementation.
 */
public interface PreguntaRepositoryPort {

    /**
     * Returns all questions ordered ascending by their display position.
     *
     * @return ordered list of all questions
     */
    List<Pregunta> findAllByOrderByOrdenAsc();

    /**
     * Persists a new question and returns the saved instance (with generated id and timestamps).
     *
     * @param pregunta the question to save
     * @return the saved, managed entity
     */
    Pregunta save(Pregunta pregunta);

    /**
     * Returns {@code true} when a question with the given camel-case {@code campo} identifier
     * already exists.
     *
     * @param campo camelCase field name to check
     * @return {@code true} if the campo is already used
     */
    boolean existsByCampo(String campo);

    /**
     * Returns all multilingual text maps from the table.
     * Used to build the deduplication context sent to the AI provider.
     *
     * @return list of texto maps (each map has language code keys and question text values)
     */
    List<Map<String, String>> findAllTextos();
}
