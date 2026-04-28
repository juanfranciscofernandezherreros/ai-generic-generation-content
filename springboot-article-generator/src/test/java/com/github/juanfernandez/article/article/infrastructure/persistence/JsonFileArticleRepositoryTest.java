package com.github.juanfernandez.article.article.infrastructure.persistence;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.juanfernandez.article.article.domain.Article;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link JsonFileArticleRepository}.
 */
class JsonFileArticleRepositoryTest {

    @Test
    void writesArticleAsPrettyJson(@TempDir Path tempDir) throws IOException {
        Article article = Article.builder()
                .title("Hello world")
                .slug("hello-world")
                .summary("summary")
                .body("<p>body</p>")
                .build();

        new JsonFileArticleRepository(tempDir, new ObjectMapper()).save(article);

        Path expected = tempDir.resolve("hello-world.json");
        assertTrue(Files.exists(expected), "Expected JSON file at " + expected);
        String content = Files.readString(expected);
        assertTrue(content.contains("\"title\""));
        assertTrue(content.contains("Hello world"));
    }

    @Test
    void createsMissingDirectoriesLazily(@TempDir Path tempDir) {
        Path nested = tempDir.resolve("a/b/c");
        Article article = Article.builder().title("T").slug("t").build();

        new JsonFileArticleRepository(nested, new ObjectMapper()).save(article);

        assertTrue(Files.exists(nested.resolve("t.json")));
    }

    @Test
    void rejectsBlankSlug(@TempDir Path tempDir) {
        Article article = Article.builder().title("T").slug("").build();

        assertThrows(IllegalStateException.class,
                () -> new JsonFileArticleRepository(tempDir, new ObjectMapper()).save(article));
    }

    @Test
    void rejectsNullArticle(@TempDir Path tempDir) {
        assertThrows(IllegalArgumentException.class,
                () -> new JsonFileArticleRepository(tempDir, new ObjectMapper()).save(null));
    }

    @Test
    void safeFileNameStripsPathSeparatorsAndTraversal() {
        assertEquals("a-b-c",     JsonFileArticleRepository.safeFileName("a/b/c"));
        assertEquals("a-b",       JsonFileArticleRepository.safeFileName("a\\b"));
        assertEquals("-evil",     JsonFileArticleRepository.safeFileName("..evil"));
    }
}
