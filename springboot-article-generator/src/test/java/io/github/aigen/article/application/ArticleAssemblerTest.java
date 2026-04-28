package io.github.aigen.article.application;

import io.github.aigen.article.domain.Article;
import io.github.aigen.shared.config.ArticleGeneratorProperties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link ArticleAssembler}.
 */
class ArticleAssemblerTest {

    private ArticleAssembler assembler;
    private ArticleGeneratorProperties properties;

    @BeforeEach
    void setUp() {
        properties = new ArticleGeneratorProperties();
        properties.setSite("https://myblog.com");
        properties.setMetaTitleMaxLength(60);
        properties.setMetaDescriptionMaxLength(160);
        TextUtils textUtils = new TextUtils();
        SeoService seoService = new SeoService(properties);
        assembler = new ArticleAssembler(properties, seoService, textUtils);
    }

    @Test
    void populatesAllRequiredSeoFields() {
        Article article = assembler.assemble(
                "Cómo usar @Data en Lombok", "Resumen breve", "<p>cuerpo del artículo</p>",
                List.of("lombok", "java"), "Java", "Lombok", "Annotations",
                "adminUser", "https://myblog.com", "es");

        assertEquals("Cómo usar @Data en Lombok", article.getTitle());
        assertEquals("como-usar-data-en-lombok",  article.getSlug());
        assertEquals("Lombok",                    article.getCategory());
        assertEquals(List.of("Annotations"),      article.getTags());
        assertEquals("adminUser",                 article.getAuthor());
        assertEquals("published",                 article.getStatus());
        assertTrue(article.isVisible());
        assertEquals("article",                   article.getOgType());
        assertEquals("https://myblog.com/post/como-usar-data-en-lombok", article.getCanonicalUrl());
        assertNotNull(article.getStructuredData());
        assertNotNull(article.getPublishDate());
        assertNotNull(article.getCreatedAt());
        assertNotNull(article.getUpdatedAt());
        assertNotNull(article.getGeneratedAt());
        assertTrue(article.getReadingTime() >= 1);
        assertTrue(article.getWordCount() >= 1);
    }

    @Test
    void truncatesMetaTitleAndDescription() {
        properties.setMetaTitleMaxLength(10);
        properties.setMetaDescriptionMaxLength(15);

        Article article = assembler.assemble(
                "Un título mucho más largo de diez", "Una descripción demasiado larga para los 15",
                "<p>body</p>", List.of(), "Cat", "Sub", null, "user", "", "es");

        assertTrue(article.getMetaTitle().length() <= 10,
                "metaTitle should be truncated, got: " + article.getMetaTitle());
        assertTrue(article.getMetaDescription().length() <= 15,
                "metaDescription should be truncated");
    }

    @Test
    void emptyTagBecomesEmptyList() {
        Article article = assembler.assemble(
                "T", "S", "<p>b</p>", List.of(), "Cat", "Sub", null, "user", "", "es");
        assertEquals(List.of(), article.getTags());
    }

    @Test
    void blankSiteProducesEmptyCanonicalUrl() {
        Article article = assembler.assemble(
                "T", "S", "<p>b</p>", List.of(), "Cat", "Sub", null, "user", "", "es");
        assertEquals("", article.getCanonicalUrl());
    }
}
