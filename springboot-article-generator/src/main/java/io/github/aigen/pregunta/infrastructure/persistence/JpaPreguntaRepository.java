package io.github.aigen.pregunta.infrastructure.persistence;

import io.github.aigen.pregunta.domain.Pregunta;
import io.github.aigen.pregunta.port.out.PreguntaRepositoryPort;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Infrastructure adapter that implements {@link PreguntaRepositoryPort} using Spring Data JPA.
 *
 * <p>This interface bridges the pregunta domain's persistence port with JPA's
 * {@code preguntas} PostgreSQL table.  Spring Data generates the implementation at runtime.
 *
 * <p>By extending both {@link JpaRepository} and {@link PreguntaRepositoryPort} this adapter
 * satisfies the output port contract while keeping all Spring Data features available.
 */
public interface JpaPreguntaRepository extends JpaRepository<Pregunta, UUID>, PreguntaRepositoryPort {

    /**
     * {@inheritDoc}
     */
    @Override
    List<Pregunta> findAllByOrderByOrdenAsc();

    /**
     * Returns the question with the highest {@code orden} value.
     * Used internally by Spring Data; the port-level ordering logic lives in the service.
     */
    java.util.Optional<Pregunta> findTopByOrderByOrdenDesc();

    /**
     * {@inheritDoc}
     */
    @Override
    boolean existsByCampo(String campo);

    /**
     * {@inheritDoc}
     */
    @Override
    @Query("SELECT p.texto FROM Pregunta p")
    List<Map<String, String>> findAllTextos();
}
