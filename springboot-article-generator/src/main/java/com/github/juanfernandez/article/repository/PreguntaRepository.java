package com.github.juanfernandez.article.repository;

import com.github.juanfernandez.article.model.Pregunta;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;

/**
 * Spring Data JPA repository for {@link Pregunta} entities stored in the
 * {@code preguntas} PostgreSQL table.
 */
public interface PreguntaRepository extends JpaRepository<Pregunta, Long> {

    /**
     * Returns all question texts in a given category (case-insensitive).
     *
     * @param categoria category name to filter by
     * @return list of matching {@link Pregunta} entities
     */
    List<Pregunta> findByCategoriaIgnoreCase(String categoria);

    /**
     * Returns every question text (the {@code pregunta} column only) from the table.
     * Used to build the deduplication context for AI generation.
     *
     * @return list of question strings
     */
    @Query("SELECT p.pregunta FROM Pregunta p")
    List<String> findAllPreguntaTexts();
}
