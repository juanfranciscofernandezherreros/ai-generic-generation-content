package io.github.aigen.pregunta.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.Arrays;
import java.util.List;

/**
 * Configuration properties for the question generator (pregunta) bounded context.
 *
 * <p>All properties are prefixed with {@code pregunta-generator} in
 * {@code application.properties} / {@code application.yml}.  Every value has a sensible
 * built-in default — no configuration is required to use the generator.
 *
 * <p>Example {@code application.yml}:
 * <pre>
 * pregunta-generator:
 *   max-context-questions: 50
 *   max-tokens: 500
 *   temperature: 0.7
 *   languages: [es, en, fr]
 * </pre>
 */
@ConfigurationProperties(prefix = "pregunta-generator")
public class PreguntaGeneratorProperties {

    /**
     * Default system message — instructs the AI to generate one new multilingual question
     * about Spanish IRPF (income tax declaration) that does not exist in the provided list.
     */
    public static final String DEFAULT_SYSTEM_MSG =
            "Eres un experto en declaraciones de la renta (IRPF) y generas preguntas para un asistente fiscal. "
            + "Tu tarea es crear UNA NUEVA pregunta en cuatro idiomas (ca, en, es, fr) que NO exista ya en la lista "
            + "proporcionada. "
            + "Devuelve ÚNICAMENTE un objeto JSON válido con esta estructura exacta, sin texto adicional:\n"
            + "{\n"
            + "  \"campo\": \"camelCaseIdentifier\",\n"
            + "  \"texto\": {\n"
            + "    \"ca\": \"...\",\n"
            + "    \"en\": \"...\",\n"
            + "    \"es\": \"...\",\n"
            + "    \"fr\": \"...\"\n"
            + "  }\n"
            + "}";

    /** Default prompt fragment used when there are no questions in the database yet. */
    public static final String DEFAULT_EMPTY_PROMPT =
            "No hay preguntas registradas todavía. Crea la primera pregunta para el asistente fiscal del IRPF.";

    /**
     * Default prompt template used when there is at least one question in the database.
     * Supports the placeholder {@code {existing}}, replaced with a bullet list
     * ({@code - <campo>: <texto-es>}) of the currently registered questions.
     */
    public static final String DEFAULT_EXISTING_PROMPT_TEMPLATE =
            "Las siguientes preguntas YA EXISTEN en el cuestionario fiscal (campo: texto en español). "
            + "NO puedes repetir ninguna de ellas ni crear algo semánticamente equivalente:\n\n"
            + "{existing}\n"
            + "Genera UNA NUEVA pregunta diferente a todas las anteriores, "
            + "relevante para la declaración de la renta española (IRPF).";

    /**
     * System message sent to the AI.  Defaults to {@link #DEFAULT_SYSTEM_MSG}.
     */
    private String systemMsg = DEFAULT_SYSTEM_MSG;

    /**
     * Prompt used when the database is empty.  Defaults to {@link #DEFAULT_EMPTY_PROMPT}.
     */
    private String emptyPrompt = DEFAULT_EMPTY_PROMPT;

    /**
     * Prompt template used when there are existing questions.
     * Defaults to {@link #DEFAULT_EXISTING_PROMPT_TEMPLATE}.
     *
     * <p>Supports the placeholder {@code {existing}} which is replaced with a bullet list of
     * already-registered questions ({@code - <campo>: <texto-es>}).
     */
    private String existingPromptTemplate = DEFAULT_EXISTING_PROMPT_TEMPLATE;

    /** Maximum number of existing questions included in the prompt context. Default: 100. */
    private int maxContextQuestions = 100;

    /** Maximum output tokens for the question-generation call. Default: 400. */
    private int maxTokens = 400;

    /** Temperature for the question-generation call (0.0 – 1.0). Default: 0.8. */
    private double temperature = 0.8;

    /**
     * Required language codes that must appear in the AI {@code texto} object.
     * Defaults to Catalan, English, Spanish and French.
     */
    private List<String> languages = Arrays.asList("ca", "en", "es", "fr");

    // ── Getters & Setters ─────────────────────────────────────────────────

    public String getSystemMsg() { return systemMsg; }
    public void setSystemMsg(String systemMsg) { this.systemMsg = systemMsg; }

    public String getEmptyPrompt() { return emptyPrompt; }
    public void setEmptyPrompt(String emptyPrompt) { this.emptyPrompt = emptyPrompt; }

    public String getExistingPromptTemplate() { return existingPromptTemplate; }
    public void setExistingPromptTemplate(String existingPromptTemplate) {
        this.existingPromptTemplate = existingPromptTemplate;
    }

    public int getMaxContextQuestions() { return maxContextQuestions; }
    public void setMaxContextQuestions(int maxContextQuestions) {
        this.maxContextQuestions = maxContextQuestions;
    }

    public int getMaxTokens() { return maxTokens; }
    public void setMaxTokens(int maxTokens) { this.maxTokens = maxTokens; }

    public double getTemperature() { return temperature; }
    public void setTemperature(double temperature) { this.temperature = temperature; }

    public List<String> getLanguages() { return languages; }
    public void setLanguages(List<String> languages) {
        this.languages = (languages != null) ? languages : Arrays.asList("ca", "en", "es", "fr");
    }
}
