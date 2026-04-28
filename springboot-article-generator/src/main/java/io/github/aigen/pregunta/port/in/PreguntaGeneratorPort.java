package io.github.aigen.pregunta.port.in;

import io.github.aigen.pregunta.domain.Pregunta;

/**
 * Primary (input) port for the pregunta bounded context.
 *
 * <p>Defines the use case exposed to the outside world: generate and persist a new
 * multilingual question.  The concrete implementation lives in the application layer
 * ({@code PreguntaGeneratorService}).
 *
 * <p>Consumers of the library can inject this interface directly to remain decoupled from the
 * implementation class.
 */
public interface PreguntaGeneratorPort {

    /**
     * Fetches all questions from the database, asks the AI to generate a new one that does not
     * already exist, saves it, and returns the persisted {@link Pregunta}.
     *
     * @return the newly created and persisted {@link Pregunta}
     * @throws RuntimeException if the AI returns an invalid or empty response
     * @throws RuntimeException if the AI generates a {@code campo} that already exists
     * @throws RuntimeException if the AI omits any of the required language keys (ca, en, es, fr)
     */
    Pregunta generateAndSave();
}
