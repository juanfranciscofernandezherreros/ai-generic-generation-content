package com.github.juanfernandez.article.service;

import com.github.juanfernandez.article.config.ArticleGeneratorProperties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for {@link PromptBuilderService}.
 */
class PromptBuilderServiceTest {

    private PromptBuilderService builder;

    @BeforeEach
    void setUp() {
        ArticleGeneratorProperties props = new ArticleGeneratorProperties();
        props.setLanguage("es");
        props.setMaxAvoidTitlesInPrompt(5);
        props.setMetaTitleMaxLength(60);
        builder = new PromptBuilderService(props);
    }

    // ── buildGenerationPrompt ─────────────────────────────────────────────

    @Test
    void buildGenerationPrompt_containsCategory() {
        String prompt = builder.buildGenerationPrompt(
                "Spring Boot", "Spring Security", "JWT", null, List.of(), "es");
        assertTrue(prompt.contains("Spring Boot"), "Prompt should contain category");
        assertTrue(prompt.contains("Spring Security"), "Prompt should contain subcategory");
        assertTrue(prompt.contains("JWT"), "Prompt should contain tag");
    }

    @Test
    void buildGenerationPrompt_containsLanguage() {
        String prompt = builder.buildGenerationPrompt(
                "Spring Boot", "General", null, null, List.of(), "en");
        assertTrue(prompt.contains("inglés"), "Prompt should contain language name in Spanish");
    }

    @Test
    void buildGenerationPrompt_withExplicitTitleUsesExactInstruction() {
        String prompt = builder.buildGenerationPrompt(
                "Spring Boot", "General", "JWT", "My Exact Title", List.of(), "es");
        assertTrue(prompt.contains("EXACTAMENTE"), "Should instruct AI to use title verbatim");
        assertTrue(prompt.contains("My Exact Title"));
    }

    @Test
    void buildGenerationPrompt_withoutTitleUsesAutoInstruction() {
        String prompt = builder.buildGenerationPrompt(
                "Spring Boot", "General", "JWT", null, List.of(), "es");
        assertFalse(prompt.contains("EXACTAMENTE"), "Should not force a specific title");
        assertTrue(prompt.contains("SEO"), "Should contain SEO instruction");
    }

    @Test
    void buildGenerationPrompt_includesAvoidTitles() {
        List<String> avoid = List.of("JWT Basics", "Spring Boot Security");
        String prompt = builder.buildGenerationPrompt(
                "Spring Boot", "General", "JWT", null, avoid, "es");
        assertTrue(prompt.contains("JWT Basics"), "Should include first avoid title");
        assertTrue(prompt.contains("Spring Boot Security"), "Should include second avoid title");
    }

    @Test
    void buildGenerationPrompt_limitsAvoidTitles() {
        List<String> many = List.of("T1", "T2", "T3", "T4", "T5", "T6", "T7");
        String prompt = builder.buildGenerationPrompt(
                "Spring Boot", "General", "JWT", null, many, "es");
        // Only first 5 should appear (maxAvoidTitlesInPrompt = 5)
        assertFalse(prompt.contains("T6"), "Should not include more than maxAvoidTitlesInPrompt");
        assertFalse(prompt.contains("T7"), "Should not include more than maxAvoidTitlesInPrompt");
    }

    @Test
    void buildGenerationPrompt_returnsJsonInstruction() {
        String prompt = builder.buildGenerationPrompt(
                "Spring Boot", "General", null, null, List.of(), "es");
        assertTrue(prompt.contains("\"title\""), "Prompt should contain JSON field 'title'");
        assertTrue(prompt.contains("\"body\""),   "Prompt should contain JSON field 'body'");
        assertTrue(prompt.contains("\"summary\""), "Prompt should contain JSON field 'summary'");
        assertTrue(prompt.contains("\"keywords\""), "Prompt should contain JSON field 'keywords'");
    }

    // ── buildTitlePrompt ──────────────────────────────────────────────────

    @Test
    void buildTitlePrompt_containsRequiredFields() {
        String prompt = builder.buildTitlePrompt(
                "Spring Boot", "Spring Security", "JWT", List.of(), "es");
        assertTrue(prompt.contains("Spring Boot"));
        assertTrue(prompt.contains("Spring Security"));
        assertTrue(prompt.contains("JWT"));
        assertTrue(prompt.contains("español"));
    }

    @Test
    void buildTitlePrompt_includesAvoidTitles() {
        String prompt = builder.buildTitlePrompt(
                "Spring Boot", "General", "JWT",
                List.of("Introduction to JWT"), "es");
        assertTrue(prompt.contains("Introduction to JWT"));
    }

    @Test
    void buildTitlePrompt_instructsOnlyTitleInOutput() {
        String prompt = builder.buildTitlePrompt(
                "Spring Boot", "General", null, List.of(), "es");
        assertTrue(prompt.contains("ÚNICAMENTE el texto del título"),
                "Prompt should instruct AI to return only the title");
    }

    // ── system messages ───────────────────────────────────────────────────

    @Test
    void getGenerationSystemMsg_returnsDefaultWhenNotConfigured() {
        String msg = builder.getGenerationSystemMsg();
        assertNotNull(msg);
        assertFalse(msg.isBlank());
        assertTrue(msg.toLowerCase().contains("seo"), "Default message should mention SEO");
    }

    @Test
    void getTitleSystemMsg_returnsDefaultWhenNotConfigured() {
        String msg = builder.getTitleSystemMsg();
        assertNotNull(msg);
        assertFalse(msg.isBlank());
    }

    @Test
    void getGenerationSystemMsg_returnsCustomWhenConfigured() {
        ArticleGeneratorProperties props = new ArticleGeneratorProperties();
        props.setGenerationSystemMsg("Custom system message");
        PromptBuilderService customBuilder = new PromptBuilderService(props);
        assertEquals("Custom system message", customBuilder.getGenerationSystemMsg());
    }

    // ── prompt templates ──────────────────────────────────────────────────

    @Test
    void buildGenerationPrompt_usesTemplateWhenConfigured() {
        ArticleGeneratorProperties props = new ArticleGeneratorProperties();
        props.setLanguage("es");
        props.setMaxAvoidTitlesInPrompt(5);
        props.setMetaTitleMaxLength(60);
        props.setGenerationPromptTemplate(
                "Write about {topic}in {lang} for {parentName}/{subcatName}. {titleInstruction}{avoidBlock}");
        PromptBuilderService templateBuilder = new PromptBuilderService(props);

        String prompt = templateBuilder.buildGenerationPrompt(
                "Spring Boot", "Security", "JWT", null, List.of(), "es");

        assertTrue(prompt.contains("español"), "Placeholder {lang} should be replaced");
        assertTrue(prompt.contains("Spring Boot"), "Placeholder {parentName} should be replaced");
        assertTrue(prompt.contains("Security"), "Placeholder {subcatName} should be replaced");
        assertTrue(prompt.contains("JWT"), "Placeholder {topic} should be replaced");
        assertFalse(prompt.contains("{lang}"), "Placeholder {lang} must not remain");
        assertFalse(prompt.contains("{parentName}"), "Placeholder {parentName} must not remain");
    }

    @Test
    void buildGenerationPrompt_templateWithExactTitle() {
        ArticleGeneratorProperties props = new ArticleGeneratorProperties();
        props.setLanguage("es");
        props.setMaxAvoidTitlesInPrompt(5);
        props.setGenerationPromptTemplate("Title instruction: {titleInstruction}");
        PromptBuilderService templateBuilder = new PromptBuilderService(props);

        String prompt = templateBuilder.buildGenerationPrompt(
                "Cat", "Sub", null, "My Exact Title", List.of(), "es");

        assertTrue(prompt.contains("EXACTAMENTE"), "Exact title instruction should be injected");
        assertTrue(prompt.contains("My Exact Title"));
    }

    @Test
    void buildGenerationPrompt_templateWithAvoidBlock() {
        ArticleGeneratorProperties props = new ArticleGeneratorProperties();
        props.setLanguage("es");
        props.setMaxAvoidTitlesInPrompt(5);
        props.setGenerationPromptTemplate("Prompt{avoidBlock}");
        PromptBuilderService templateBuilder = new PromptBuilderService(props);

        String prompt = templateBuilder.buildGenerationPrompt(
                "Cat", "Sub", null, null, List.of("JWT Basics"), "es");

        assertTrue(prompt.contains("JWT Basics"), "Avoid-titles block should be injected");
    }

    @Test
    void buildTitlePrompt_usesTemplateWhenConfigured() {
        ArticleGeneratorProperties props = new ArticleGeneratorProperties();
        props.setLanguage("es");
        props.setMaxAvoidTitlesInPrompt(5);
        props.setMetaTitleMaxLength(60);
        props.setTitlePromptTemplate(
                "Title in {lang} {topic}for {parentName}/{subcatName}, max {maxLen} chars.{avoidBlock}");
        PromptBuilderService templateBuilder = new PromptBuilderService(props);

        String prompt = templateBuilder.buildTitlePrompt(
                "Spring Boot", "Security", "JWT", List.of(), "en");

        assertTrue(prompt.contains("inglés"), "Placeholder {lang} should be replaced");
        assertTrue(prompt.contains("Spring Boot"), "Placeholder {parentName} should be replaced");
        assertTrue(prompt.contains("Security"), "Placeholder {subcatName} should be replaced");
        assertTrue(prompt.contains("JWT"), "Placeholder {topic} should be replaced");
        assertTrue(prompt.contains("60"), "Placeholder {maxLen} should be replaced");
        assertFalse(prompt.contains("{lang}"), "Placeholder {lang} must not remain");
        assertFalse(prompt.contains("{maxLen}"), "Placeholder {maxLen} must not remain");
    }

    @Test
    void buildTitlePrompt_templateWithAvoidBlock() {
        ArticleGeneratorProperties props = new ArticleGeneratorProperties();
        props.setLanguage("es");
        props.setMaxAvoidTitlesInPrompt(5);
        props.setMetaTitleMaxLength(60);
        props.setTitlePromptTemplate("Title prompt{avoidBlock}");
        PromptBuilderService templateBuilder = new PromptBuilderService(props);

        String prompt = templateBuilder.buildTitlePrompt(
                "Cat", "Sub", null, List.of("Existing Title"), "es");

        assertTrue(prompt.contains("Existing Title"), "Avoid-titles block should be injected");
    }
}