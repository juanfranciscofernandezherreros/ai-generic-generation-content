package com.github.juanfernandez.article.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.LocalDateTime;

/**
 * JPA entity that maps to the {@code preguntas} table in PostgreSQL.
 *
 * <p>Minimal DDL to create the table:
 * <pre>{@code
 * CREATE TABLE preguntas (
 *     id          BIGSERIAL PRIMARY KEY,
 *     pregunta    TEXT        NOT NULL,
 *     categoria   VARCHAR(255),
 *     creada_en   TIMESTAMP   NOT NULL DEFAULT now()
 * );
 * }</pre>
 */
@Entity
@Table(name = "preguntas")
public class Pregunta {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** The question text. */
    @Column(nullable = false, columnDefinition = "TEXT")
    private String pregunta;

    /** Optional category that groups related questions. */
    @Column(length = 255)
    private String categoria;

    /** Timestamp when the question was created. */
    @Column(name = "creada_en", nullable = false)
    private LocalDateTime creadaEn;

    // ── Constructors ──────────────────────────────────────────────────────

    public Pregunta() {}

    public Pregunta(String pregunta, String categoria) {
        this.pregunta  = pregunta;
        this.categoria = categoria;
        this.creadaEn  = LocalDateTime.now();
    }

    // ── Getters & Setters ─────────────────────────────────────────────────

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getPregunta() { return pregunta; }
    public void setPregunta(String pregunta) { this.pregunta = pregunta; }

    public String getCategoria() { return categoria; }
    public void setCategoria(String categoria) { this.categoria = categoria; }

    public LocalDateTime getCreadaEn() { return creadaEn; }
    public void setCreadaEn(LocalDateTime creadaEn) { this.creadaEn = creadaEn; }

    @Override
    public String toString() {
        return "Pregunta{id=" + id + ", pregunta='" + pregunta + "', categoria='" + categoria + "'}";
    }
}
