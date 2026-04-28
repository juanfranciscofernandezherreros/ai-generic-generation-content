package io.github.aigen.shared.config;

import io.github.aigen.shared.ai.AiConfig;
import io.github.aigen.shared.ai.AiProvider;
import io.github.aigen.shared.ai.RetryConfig;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Configuration properties for the Article Generator Spring Boot Starter.
 *
 * <p>All properties are prefixed with {@code article-generator} in
 * {@code application.properties} / {@code application.yml}.
 *
 * <p>Example {@code application.properties}:
 * <pre>
 * article-generator.provider=openai
 * article-generator.model=gpt-4o
 * article-generator.openai-api-key=${OPENAIAPIKEY}
 * article-generator.site=https://myblog.com
 * article-generator.author-username=adminUser
 * article-generator.language=es
 * </pre>
 *
 * <p>Example {@code application.yml}:
 * <pre>
 * article-generator:
 *   provider: openai
 *   model: gpt-4o
 *   openai-api-key: ${OPENAIAPIKEY}
 *   site: https://myblog.com
 *   language: es
 * </pre>
 */
@ConfigurationProperties(prefix = "article-generator")
public class ArticleGeneratorProperties implements AiConfig, RetryConfig {

    // ── AI provider selection ─────────────────────────────────────────────

    /**
     * AI provider to use.
     * <ul>
     *   <li>{@code AUTO} (default) — auto-detect: Gemini if model starts with {@code gemini-},
     *       Ollama if {@code ollama-base-url} is set, otherwise OpenAI.</li>
     *   <li>{@code OPENAI}     — force OpenAI GPT models.</li>
     *   <li>{@code GEMINI}     — force Google Gemini.</li>
     *   <li>{@code OLLAMA}     — force Ollama local server.</li>
     *   <li>{@code ANTHROPIC}  — force Anthropic Claude (requires LangChain4j
     *       {@code langchain4j-anthropic-spring-boot-starter}).</li>
     * </ul>
     */
    private AiProvider provider = AiProvider.AUTO;

    /** AI model name. Default: {@code gpt-4o}. */
    private String model = "gpt-4o";

    // ── API credentials ───────────────────────────────────────────────────

    /** OpenAI API key — required when using OpenAI provider. Maps to env {@code OPENAIAPIKEY}. */
    private String openaiApiKey;

    /** Google Gemini API key — required when using Gemini provider. Maps to env {@code GEMINI_API_KEY}. */
    private String geminiApiKey;

    /** Ollama base URL (e.g. {@code http://localhost:11434}). Required for Ollama provider. */
    private String ollamaBaseUrl;

    // ── Article defaults ─────────────────────────────────────────────────

    /** Base site URL used to build canonical URLs (e.g. {@code https://myblog.com}). */
    private String site = "";

    /** Default author username. Default: {@code adminUser}. */
    private String authorUsername = "adminUser";

    /** Default article language (ISO 639-1 code). Default: {@code es}. */
    private String language = "es";

    /**
     * Optional directory where generated articles are persisted as {@code <slug>.json}.
     * When unset (default) generated articles are returned to the caller but not written
     * to disk.
     */
    private String outputDir;

    // ── AI generation parameters ──────────────────────────────────────────

    /** Temperature for article body generation (0.0 – 1.0). Default: {@code 0.7}. */
    private double temperatureArticle = 0.7;

    /** Temperature for title-only generation (0.0 – 1.0). Default: {@code 0.9}. */
    private double temperatureTitle = 0.9;

    /** Maximum output tokens for article generation. Default: {@code 8096}. */
    private int maxArticleTokens = 8096;

    /** Maximum output tokens for title-only generation. Default: {@code 100}. */
    private int maxTitleTokens = 100;

    // ── Deduplication & retries ───────────────────────────────────────────

    /**
     * Similarity threshold (0.0 – 1.0) above which a title is considered a duplicate.
     * Default: {@code 0.86}.
     */
    private double similarityThreshold = 0.86;

    /** Maximum attempts to regenerate a unique title (Phase 2). Default: {@code 5}. */
    private int maxTitleRetries = 5;

    /** Maximum retries for transient AI API errors. Default: {@code 3}. */
    private int maxApiRetries = 3;

    /** Base delay in seconds for exponential back-off. Default: {@code 2}. */
    private int retryBaseDelaySeconds = 2;

    // ── SEO metadata limits ───────────────────────────────────────────────

    /** Maximum character length for {@code metaTitle}. Default: {@code 60}. */
    private int metaTitleMaxLength = 60;

    /** Maximum character length for {@code metaDescription}. Default: {@code 160}. */
    private int metaDescriptionMaxLength = 160;

    /** Maximum number of avoid-titles included in the AI prompt. Default: {@code 5}. */
    private int maxAvoidTitlesInPrompt = 5;

    // ── System messages ───────────────────────────────────────────────────

    /**
     * System message sent to the AI for article generation.
     * Overrides the built-in default when set.
     */
    private String generationSystemMsg;

    /**
     * System message sent to the AI for title-only generation.
     * Overrides the built-in default when set.
     */
    private String titleSystemMsg;

    // ── Prompt templates ──────────────────────────────────────────────────

    /**
     * Template for the user prompt sent to the AI for full article generation.
     * When set, overrides the built-in default prompt.
     *
     * <p>Supported placeholders:
     * <ul>
     *   <li>{@code {lang}}             — resolved language name (e.g. {@code español})</li>
     *   <li>{@code {topic}}            — tag/topic fragment (e.g. {@code sobre "JWT" }), empty when not set</li>
     *   <li>{@code {parentName}}       — category name</li>
     *   <li>{@code {subcatName}}       — sub-category name</li>
     *   <li>{@code {titleInstruction}} — title instruction fragment (verbatim or SEO-auto)</li>
     *   <li>{@code {avoidBlock}}       — avoid-titles fragment, empty when list is empty</li>
     * </ul>
     */
    private String generationPromptTemplate;

    /**
     * Template for the user prompt sent to the AI for title-only generation.
     * When set, overrides the built-in default prompt.
     *
     * <p>Supported placeholders:
     * <ul>
     *   <li>{@code {lang}}       — resolved language name (e.g. {@code español})</li>
     *   <li>{@code {topic}}      — tag/topic fragment, empty when not set</li>
     *   <li>{@code {parentName}} — category name</li>
     *   <li>{@code {subcatName}} — sub-category name</li>
     *   <li>{@code {maxLen}}     — maximum title length in characters</li>
     *   <li>{@code {avoidBlock}} — avoid-titles fragment, empty when list is empty</li>
     * </ul>
     */
    private String titlePromptTemplate;

    // ── Getters & Setters ─────────────────────────────────────────────────

    public AiProvider getProvider() { return provider; }
    public void setProvider(AiProvider provider) { this.provider = provider; }

    public String getModel() { return model; }
    public void setModel(String model) { this.model = model; }

    public String getOpenaiApiKey() { return openaiApiKey; }
    public void setOpenaiApiKey(String openaiApiKey) { this.openaiApiKey = openaiApiKey; }

    public String getGeminiApiKey() { return geminiApiKey; }
    public void setGeminiApiKey(String geminiApiKey) { this.geminiApiKey = geminiApiKey; }

    public String getOllamaBaseUrl() { return ollamaBaseUrl; }
    public void setOllamaBaseUrl(String ollamaBaseUrl) { this.ollamaBaseUrl = ollamaBaseUrl; }

    public String getSite() { return site; }
    public void setSite(String site) { this.site = site; }

    public String getAuthorUsername() { return authorUsername; }
    public void setAuthorUsername(String authorUsername) { this.authorUsername = authorUsername; }

    public String getLanguage() { return language; }
    public void setLanguage(String language) { this.language = language; }

    public String getOutputDir() { return outputDir; }
    public void setOutputDir(String outputDir) { this.outputDir = outputDir; }

    public double getTemperatureArticle() { return temperatureArticle; }
    public void setTemperatureArticle(double temperatureArticle) { this.temperatureArticle = temperatureArticle; }

    public double getTemperatureTitle() { return temperatureTitle; }
    public void setTemperatureTitle(double temperatureTitle) { this.temperatureTitle = temperatureTitle; }

    public int getMaxArticleTokens() { return maxArticleTokens; }
    public void setMaxArticleTokens(int maxArticleTokens) { this.maxArticleTokens = maxArticleTokens; }

    public int getMaxTitleTokens() { return maxTitleTokens; }
    public void setMaxTitleTokens(int maxTitleTokens) { this.maxTitleTokens = maxTitleTokens; }

    public double getSimilarityThreshold() { return similarityThreshold; }
    public void setSimilarityThreshold(double similarityThreshold) { this.similarityThreshold = similarityThreshold; }

    public int getMaxTitleRetries() { return maxTitleRetries; }
    public void setMaxTitleRetries(int maxTitleRetries) { this.maxTitleRetries = maxTitleRetries; }

    public int getMaxApiRetries() { return maxApiRetries; }
    public void setMaxApiRetries(int maxApiRetries) { this.maxApiRetries = maxApiRetries; }

    public int getRetryBaseDelaySeconds() { return retryBaseDelaySeconds; }
    public void setRetryBaseDelaySeconds(int retryBaseDelaySeconds) { this.retryBaseDelaySeconds = retryBaseDelaySeconds; }

    public int getMetaTitleMaxLength() { return metaTitleMaxLength; }
    public void setMetaTitleMaxLength(int metaTitleMaxLength) { this.metaTitleMaxLength = metaTitleMaxLength; }

    public int getMetaDescriptionMaxLength() { return metaDescriptionMaxLength; }
    public void setMetaDescriptionMaxLength(int metaDescriptionMaxLength) { this.metaDescriptionMaxLength = metaDescriptionMaxLength; }

    public int getMaxAvoidTitlesInPrompt() { return maxAvoidTitlesInPrompt; }
    public void setMaxAvoidTitlesInPrompt(int maxAvoidTitlesInPrompt) { this.maxAvoidTitlesInPrompt = maxAvoidTitlesInPrompt; }

    public String getGenerationSystemMsg() { return generationSystemMsg; }
    public void setGenerationSystemMsg(String generationSystemMsg) { this.generationSystemMsg = generationSystemMsg; }

    public String getTitleSystemMsg() { return titleSystemMsg; }
    public void setTitleSystemMsg(String titleSystemMsg) { this.titleSystemMsg = titleSystemMsg; }

    public String getGenerationPromptTemplate() { return generationPromptTemplate; }
    public void setGenerationPromptTemplate(String generationPromptTemplate) { this.generationPromptTemplate = generationPromptTemplate; }

    public String getTitlePromptTemplate() { return titlePromptTemplate; }
    public void setTitlePromptTemplate(String titlePromptTemplate) { this.titlePromptTemplate = titlePromptTemplate; }
}
