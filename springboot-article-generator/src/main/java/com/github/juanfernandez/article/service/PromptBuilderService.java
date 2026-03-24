package com.github.juanfernandez.article.service;

import com.github.juanfernandez.article.config.ArticleGeneratorProperties;

import java.util.List;
import java.util.Map;

/**
 * Builds prompts for AI article and title generation.
 *
 * <p>Mirrors the Python {@code prompts.py} module. Prompts are written in the configured
 * language and include detailed SEO on-page instructions.
 */
public class PromptBuilderService {

    private static final String DEFAULT_GENERATION_SYSTEM_MSG =
            "Eres redactor técnico sénior y experto en SEO especializado en tecnología y desarrollo de software. "
            + "Generas contenido optimizado para motores de búsqueda con HTML semántico, "
            + "estructura de encabezados jerárquica (h1 > h2 > h3), uso estratégico de palabras clave "
            + "y metadatos precisos. "
            + "El contenido que redactas está siempre relacionado con la categoría y el tag indicados en el prompt. "
            + "Devuelves SOLO JSON válido con: title, summary, body (HTML semántico), keywords.";

    private static final String DEFAULT_TITLE_SYSTEM_MSG =
            "Eres experto en SEO técnico. "
            + "Devuelve solo el título solicitado, sin comillas ni texto adicional.";

    /** Map of ISO 639-1 codes to language names in Spanish (used in prompts). */
    private static final Map<String, String> LANGUAGE_NAMES = Map.ofEntries(
            Map.entry("es", "español"),
            Map.entry("en", "inglés"),
            Map.entry("fr", "francés"),
            Map.entry("de", "alemán"),
            Map.entry("it", "italiano"),
            Map.entry("pt", "portugués"),
            Map.entry("nl", "neerlandés"),
            Map.entry("pl", "polaco"),
            Map.entry("ru", "ruso"),
            Map.entry("zh", "chino"),
            Map.entry("ja", "japonés"),
            Map.entry("ar", "árabe")
    );

    private final ArticleGeneratorProperties properties;

    public PromptBuilderService(ArticleGeneratorProperties properties) {
        this.properties = properties;
    }

    // ── Public API ────────────────────────────────────────────────────────

    /**
     * Returns the system message used for article body generation.
     * Uses the custom value from properties when configured, otherwise returns the built-in default.
     */
    public String getGenerationSystemMsg() {
        String custom = properties.getGenerationSystemMsg();
        return (custom != null && !custom.isBlank()) ? custom : DEFAULT_GENERATION_SYSTEM_MSG;
    }

    /**
     * Returns the system message used for title-only generation.
     * Uses the custom value from properties when configured, otherwise returns the built-in default.
     */
    public String getTitleSystemMsg() {
        String custom = properties.getTitleSystemMsg();
        return (custom != null && !custom.isBlank()) ? custom : DEFAULT_TITLE_SYSTEM_MSG;
    }

    /**
     * Builds the full article generation prompt (title + summary + HTML body + keywords).
     *
     * @param parentName   category name (e.g. {@code "Spring Boot"})
     * @param subcatName   sub-category name (e.g. {@code "Spring Security"})
     * @param tagText      topic / tag (may be {@code null})
     * @param title        explicit title for the AI to use verbatim (may be {@code null})
     * @param avoidTitles  titles to exclude from the AI's output
     * @param language     ISO 639-1 language code
     * @return prompt string ready to send to the AI
     */
    public String buildGenerationPrompt(
            String parentName,
            String subcatName,
            String tagText,
            String title,
            List<String> avoidTitles,
            String language) {

        String lang = languageName(language);
        String topic = (tagText != null && !tagText.isBlank()) ? "sobre \"" + tagText + "\" " : "";
        String titleInstruction;
        if (title != null && !title.isBlank()) {
            titleInstruction = "title: usa EXACTAMENTE este título: \"" + title + "\". No lo modifiques.";
        } else {
            titleInstruction = "title: optimizado para SEO y CTR, conciso (máx. 60 caracteres), incluye palabra clave principal al inicio.";
        }

        String avoidBlock = buildAvoidBlock(avoidTitles,
                "\nEvita títulos iguales o muy similares a: ", "\"; \"", "\"", "\"");

        return "Artículo SEO en " + lang + " " + topic
                + "(categoría: \"" + parentName + "\", subcategoría: \"" + subcatName + "\").\n"
                + "Devuelve SOLO JSON: {\"title\":\"...\",\"summary\":\"...\",\"body\":\"...\",\"keywords\":[...]}\n\n"
                + titleInstruction + "\n"
                + "summary: meta-descripción SEO (máx. 160 caracteres), incluye palabra clave, llamada a la acción implícita.\n"
                + "keywords: 5-7 palabras clave SEO en minúsculas (long-tail incluidas), sin repetir el título exacto.\n"
                + "body (HTML semántico bien cerrado, optimizado para SEO on-page):\n"
                + "- <h1> con título (sin emojis), palabra clave principal incluida.\n"
                + "- Intro <p> que enganche, presente el problema y contenga la keyword principal.\n"
                + "- 3-5 secciones <h2> con keywords secundarias: explicación técnica, buenas prácticas, casos reales.\n"
                + "- Subsecciones <h3> donde sea necesario para profundizar.\n"
                + "- Código en <pre><code class=\"language-...\">. Funcional, copiable, con comentarios descriptivos.\n"
                + "- Usa <strong> y <em> para resaltar términos clave (sin abusar).\n"
                + "- <h2> FAQ (Preguntas frecuentes): 3-5 preguntas en <h3> con respuestas en <p>. Redacta preguntas como búsquedas reales de usuarios.\n"
                + "- <h2> Conclusión con resumen de puntos clave y CTA (llamada a la acción).\n"
                + "- Listas <ul>/<ol> para ventajas, pasos o comparativas.\n"
                + "- Párrafos cortos (3-4 líneas máx.) para mejorar la legibilidad.\n\n"
                + "Tono profesional, sin relleno. JSON con comillas escapadas."
                + avoidBlock + "\n";
    }

    /**
     * Builds a lightweight title-only prompt (much cheaper than the full article prompt).
     * Used in Phase 2 of the deduplication loop.
     *
     * @param parentName  category name
     * @param subcatName  sub-category name
     * @param tagText     topic / tag (may be {@code null})
     * @param avoidTitles titles to exclude
     * @param language    ISO 639-1 language code
     * @return prompt string ready to send to the AI
     */
    public String buildTitlePrompt(
            String parentName,
            String subcatName,
            String tagText,
            List<String> avoidTitles,
            String language) {

        String lang = languageName(language);
        String topic = (tagText != null && !tagText.isBlank()) ? "para el tema \"" + tagText + "\" " : "";
        int maxLen = properties.getMetaTitleMaxLength();

        String avoidBlock = buildAvoidBlock(avoidTitles,
                "\nEvita títulos iguales o muy similares a cualquiera de estos: ", "\"; \"", "\"", "\"");

        return "Genera un título de artículo técnico en " + lang + " " + topic
                + "(categoría: \"" + parentName + "\", subcategoría: \"" + subcatName + "\").\n"
                + "Requisitos: atractivo, conciso (máx. " + maxLen + " caracteres), "
                + "optimizado para SEO, incluye la palabra clave principal." + avoidBlock + "\n"
                + "Devuelve ÚNICAMENTE el texto del título, sin comillas ni texto adicional.";
    }

    // ── Private helpers ───────────────────────────────────────────────────

    private String languageName(String code) {
        if (code == null) return LANGUAGE_NAMES.getOrDefault(properties.getLanguage(), properties.getLanguage());
        return LANGUAGE_NAMES.getOrDefault(code.toLowerCase(), code);
    }

    private String buildAvoidBlock(List<String> avoidTitles, String prefix, String separator,
                                   String itemPrefix, String itemSuffix) {
        if (avoidTitles == null || avoidTitles.isEmpty()) return "";
        int max = properties.getMaxAvoidTitlesInPrompt();
        List<String> limited = avoidTitles.size() > max ? avoidTitles.subList(0, max) : avoidTitles;
        StringBuilder sb = new StringBuilder(prefix);
        for (int i = 0; i < limited.size(); i++) {
            if (i > 0) sb.append(separator);
            sb.append(itemPrefix).append(limited.get(i).replace("\"", "\\\"")).append(itemSuffix);
        }
        return sb.toString();
    }
}
