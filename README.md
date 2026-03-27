# Spring Boot Article Generator

Starter de Spring Boot para generar artículos técnicos con IA y metadatos SEO completos.  
Integración nativa con **LangChain4j** para **OpenAI**, **Google Gemini** y **Ollama** (local).

---

## Contenido

- [¿Qué incluye?](#qué-incluye)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Build y tests](#build-y-tests)
- [Cómo usarlo](#cómo-usarlo-en-otro-proyecto-spring-boot)
  - [1. Instalar el starter](#1-instalar-el-starter-localmente)
  - [2. Agregar dependencia](#2-agregar-dependencia-en-tu-proyecto-spring-boot)
  - [3. Configurar proveedores](#3-configurar-propiedades)
  - [4. Inyectar y usar el servicio](#4-inyectar-y-usar-articlegeneratorservice)
- [Referencia de propiedades](#referencia-de-propiedades)
- [Algoritmo de deduplicación de títulos](#algoritmo-de-deduplicación-de-títulos)
- [Ejemplo end-to-end](#ejemplo-de-uso-end-to-end)
- [Modelo de entrada](#modelo-de-entrada-articlerequest)
- [Modelo de respuesta](#modelo-de-respuesta-article)
- [Notas rápidas](#notas-rápidas)

---

## ¿Qué incluye?

- `springboot-article-generator/` — librería `article-generator-spring-boot-starter` con autoconfiguración Spring Boot.
- Servicio principal listo para inyectar: `ArticleGeneratorService`.
- Integración **LangChain4j 1.0.0-beta5** como método preferido para los tres proveedores:
  - `langchain4j-open-ai-spring-boot-starter` — OpenAI (GPT)
  - `langchain4j-google-ai-gemini-spring-boot-starter` — Google Gemini
  - `langchain4j-ollama-spring-boot-starter` — Ollama (local)
- Soporte de proveedores IA (todos disponibles también por REST directo como fallback):
  - **OpenAI** (GPT) — vía LangChain4j `ChatModel` (recomendado) o REST directo
  - **Google Gemini** — vía LangChain4j `ChatModel` (recomendado) o REST directo
  - **Ollama** (local) — vía LangChain4j `ChatModel` (recomendado) o REST directo
- Generación de artículos con HTML semántico, metadatos SEO completos, Schema.org JSON-LD y Open Graph.
- Algoritmo de deduplicación de títulos en dos fases.
- Reintentos automáticos con _exponential back-off_ para errores transitorios de red.

---

## Arquitectura

```
ArticleGeneratorService          ← orquesta el pipeline completo
  ├─ PromptBuilderService        ← construye los prompts para la IA en el idioma indicado
  ├─ AiClientService             ← cliente HTTP para los proveedores IA
  │    ├─ LangChain4j ChatModel  ← OpenAI, Google Gemini u Ollama (recomendado, opcional)
  │    ├─ OpenAI REST directo    ← fallback sin LangChain4j
  │    ├─ Google Gemini REST     ← fallback sin LangChain4j
  │    └─ Ollama REST            ← fallback sin LangChain4j (endpoint OpenAI-compatible)
  ├─ SeoService                  ← genera canonical URL y Schema.org TechArticle JSON-LD
  └─ TextUtils                   ← slugificación, similitud de títulos, recuento de palabras
```

| Clase | Propósito |
|-------|-----------|
| `ArticleGeneratorService` | Pipeline principal: generación, deduplicación, enriquecimiento SEO |
| `AiClientService` | Llamadas a la IA (LangChain4j / REST directo) y extracción de JSON |
| `PromptBuilderService` | Construcción de prompts multilingüe con instrucciones SEO |
| `SeoService` | URLs canónicas y datos estructurados Schema.org |
| `TextUtils` | Slugs, similitud de títulos (LCS ratio), conteo de palabras, tiempo de lectura |
| `ArticleGeneratorProperties` | Propiedades `@ConfigurationProperties(prefix = "article-generator")` |
| `Article` | DTO de salida con contenido + metadatos SEO + Open Graph + estadísticas |
| `ArticleRequest` | DTO de entrada para la generación |
| `AiProvider` | Enum: `AUTO`, `OPENAI`, `GEMINI`, `OLLAMA` |

La autoconfiguración registra todos los beans con `@ConditionalOnMissingBean`, por lo que cualquier bean puede ser sobreescrito por el proyecto consumidor.

---

## Requisitos

- Java 17+
- Maven 3.9+
- Spring Boot 3.x en el proyecto consumidor

---

## Build y tests

```bash
cd springboot-article-generator
mvn test
```

---

## Cómo usarlo en **otro proyecto Spring Boot**

### 1) Instalar el starter localmente

Desde la raíz de este repositorio:

```bash
cd springboot-article-generator
mvn clean install
```

Esto instalará el artefacto en tu repositorio local (`~/.m2/repository`).

### 2) Agregar dependencia en tu proyecto Spring Boot

En el `pom.xml` del **otro proyecto**:

```xml
<dependency>
    <groupId>com.github.juanfernandez</groupId>
    <artifactId>article-generator-spring-boot-starter</artifactId>
    <version>1.0.1</version>
</dependency>
```

> Si quieres usar LangChain4j, añade también el starter del proveedor deseado en el proyecto consumidor
> (el starter los declara como dependencias `optional`):
>
> ```xml
> <!-- OpenAI -->
> <dependency>
>     <groupId>dev.langchain4j</groupId>
>     <artifactId>langchain4j-open-ai-spring-boot-starter</artifactId>
>     <version>1.0.0-beta5</version>
> </dependency>
>
> <!-- Google Gemini -->
> <dependency>
>     <groupId>dev.langchain4j</groupId>
>     <artifactId>langchain4j-google-ai-gemini-spring-boot-starter</artifactId>
>     <version>1.0.0-beta5</version>
> </dependency>
>
> <!-- Ollama -->
> <dependency>
>     <groupId>dev.langchain4j</groupId>
>     <artifactId>langchain4j-ollama-spring-boot-starter</artifactId>
>     <version>1.0.0-beta5</version>
> </dependency>
> ```

### 3) Configurar propiedades

#### Opción A — OpenAI vía **LangChain4j** ✅ Recomendado

Añade en `application.yml`:

```yaml
langchain4j:
  open-ai:
    chat-model:
      api-key: ${OPENAIAPIKEY}
      model-name: gpt-4o          # cualquier modelo GPT
      temperature: 0.7
      timeout: PT60S
      log-requests: true
      log-responses: true

article-generator:
  site: https://mi-blog.com
  author-username: adminUser
  language: es
```

> El starter detecta automáticamente el bean `ChatModel` creado por la autoconfiguración de LangChain4j
> y lo inyecta en `AiClientService`.
> No es necesario definir `article-generator.provider` ni `article-generator.openai-api-key`.
>
> LangChain4j gestiona el modelo, la clave API, la temperatura, el timeout y el logging de forma transparente.

#### Opción B — Google Gemini vía **LangChain4j** ✅ Recomendado

```yaml
langchain4j:
  google-ai-gemini:
    chat-model:
      api-key: ${GEMINI_API_KEY}
      model-name: gemini-2.0-flash
      temperature: 0.7
      log-requests: true
      log-responses: true

article-generator:
  site: https://mi-blog.com
  author-username: adminUser
  language: es
```

#### Opción C — Ollama vía **LangChain4j** ✅ Recomendado

```yaml
langchain4j:
  ollama:
    chat-model:
      base-url: http://localhost:11434
      model-name: llama3
      temperature: 0.7
      timeout: PT120S

article-generator:
  site: https://mi-blog.com
  author-username: adminUser
  language: es
```

#### Opción D — OpenAI REST directo (sin LangChain4j)

```yaml
article-generator:
  provider: openai
  model: gpt-4o
  openai-api-key: ${OPENAIAPIKEY}
  site: https://mi-blog.com
  author-username: adminUser
  language: es
```

#### Opción E — Google Gemini REST directo (sin LangChain4j)

```yaml
article-generator:
  provider: gemini
  model: gemini-2.0-flash
  gemini-api-key: ${GEMINI_API_KEY}
  site: https://mi-blog.com
  author-username: adminUser
  language: es
```

#### Opción F — Ollama REST directo (sin LangChain4j)

```yaml
article-generator:
  provider: ollama
  model: llama3
  ollama-base-url: http://localhost:11434
  site: https://mi-blog.com
  author-username: adminUser
  language: es
```

#### Detección automática de proveedor (`AUTO`)

Si no se especifica `article-generator.provider` (o se deja en `AUTO`), el starter aplica la siguiente lógica:

1. Si hay un bean `ChatModel` de LangChain4j → **proveedor configurado vía LangChain4j** (OpenAI, Gemini u Ollama según el starter que hayas añadido)
2. Si `article-generator.model` empieza por `gemini-` → **Gemini REST directo**
3. Si `article-generator.ollama-base-url` está definido → **Ollama REST directo**
4. Si no → **OpenAI REST directo** (requiere `article-generator.openai-api-key`)

### 4) Inyectar y usar `ArticleGeneratorService`

```java
package com.example.demo.web;

import com.github.juanfernandez.article.model.Article;
import com.github.juanfernandez.article.model.ArticleRequest;
import com.github.juanfernandez.article.service.ArticleGeneratorService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/articles")
public class ArticleController {

    private final ArticleGeneratorService articleGeneratorService;

    public ArticleController(ArticleGeneratorService articleGeneratorService) {
        this.articleGeneratorService = articleGeneratorService;
    }

    @PostMapping("/generate")
    public Article generate(@RequestBody GenerateArticleInput input) {
        ArticleRequest request = ArticleRequest.builder()
                .category(input.category())
                .subcategory(input.subcategory())
                .tag(input.tag())
                .title(input.title())           // optional: forces an exact title
                .language(input.language())
                .site(input.site())
                .authorUsername(input.authorUsername())
                .avoidTitles(input.avoidTitles())
                .build();

        return articleGeneratorService.generateArticle(request);
    }

    public record GenerateArticleInput(
            String category,
            String subcategory,
            String tag,
            String title,           // optional: if provided, the AI generates the body around this title
            String language,
            String site,
            String authorUsername,
            List<String> avoidTitles
    ) {}
}
```

---

## Referencia de propiedades

Todas las propiedades tienen el prefijo `article-generator`.

### Proveedor IA

| Propiedad | Tipo | Defecto | Descripción |
|-----------|------|---------|-------------|
| `provider` | `AUTO` \| `OPENAI` \| `GEMINI` \| `OLLAMA` | `AUTO` | Proveedor IA activo |
| `model` | `String` | `gpt-4o` | Nombre del modelo |
| `openai-api-key` | `String` | — | Clave API de OpenAI |
| `gemini-api-key` | `String` | — | Clave API de Google Gemini |
| `ollama-base-url` | `String` | — | URL base del servidor Ollama (p.e. `http://localhost:11434`) |

### Artículo por defecto

| Propiedad | Tipo | Defecto | Descripción |
|-----------|------|---------|-------------|
| `site` | `String` | `""` | URL base para construir las URLs canónicas |
| `author-username` | `String` | `adminUser` | Autor por defecto |
| `language` | `String` | `es` | Idioma ISO 639-1 (p.e. `es`, `en`) |

### Parámetros de generación IA

| Propiedad | Tipo | Defecto | Descripción |
|-----------|------|---------|-------------|
| `temperature-article` | `double` | `0.7` | Temperatura para el cuerpo del artículo (0.0–1.0) |
| `temperature-title` | `double` | `0.9` | Temperatura para la regeneración de títulos (0.0–1.0) |
| `max-article-tokens` | `int` | `8096` | Tokens máximos de salida para el artículo completo |
| `max-title-tokens` | `int` | `100` | Tokens máximos de salida solo para el título |

### Deduplicación y reintentos

| Propiedad | Tipo | Defecto | Descripción |
|-----------|------|---------|-------------|
| `similarity-threshold` | `double` | `0.86` | Umbral de similitud para considerar un título duplicado (0.0–1.0) |
| `max-title-retries` | `int` | `5` | Intentos máximos para regenerar un título único (Fase 2) |
| `max-api-retries` | `int` | `3` | Reintentos ante errores transitorios de la API |
| `retry-base-delay-seconds` | `int` | `2` | Retardo base (segundos) para _exponential back-off_ |

### Límites de metadatos SEO

| Propiedad | Tipo | Defecto | Descripción |
|-----------|------|---------|-------------|
| `meta-title-max-length` | `int` | `60` | Longitud máxima del `metaTitle` (caracteres) |
| `meta-description-max-length` | `int` | `160` | Longitud máxima de `metaDescription` (caracteres) |
| `max-avoid-titles-in-prompt` | `int` | `5` | Máximo de títulos a evitar incluidos en el prompt |

### Mensajes de sistema personalizables

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `generation-system-msg` | `String` | Sobreescribe el mensaje de sistema para la generación del artículo |
| `title-system-msg` | `String` | Sobreescribe el mensaje de sistema para la regeneración del título |

---

## Algoritmo de deduplicación de títulos

El starter aplica un proceso en **dos fases** para garantizar títulos únicos:

**Fase 1 — Generación completa**

1. La IA genera el artículo completo: título, resumen, cuerpo HTML y palabras clave.
2. Se calcula la similitud del título generado con cada entrada de `avoidTitles` usando la métrica de similitud LCS (`2 * LCS / (|a| + |b|)`, equivalente a Python's `SequenceMatcher.ratio()`).
3. Si la similitud es inferior al umbral (`similarity-threshold`, defecto `0.86`), el artículo se acepta → **fin**.
4. Si el título es demasiado similar, se activa la Fase 2.

**Fase 2 — Regeneración solo del título**

1. Se reutiliza el cuerpo HTML generado en la Fase 1.
2. Se solicita a la IA que genere únicamente un nuevo título (hasta `max-title-retries` intentos).
3. Cada título candidato se comprueba contra `avoidTitles`.
4. El primer título que supere la comprobación se aplica (se actualiza el `<h1>` en el cuerpo).
5. Si ningún intento produce un título único, se lanza una excepción.

> La deduplicación de fases se omite por completo cuando se proporciona un `title` explícito en el `ArticleRequest`.

---

## Ejemplo de uso end-to-end

### Request

```bash
curl -X POST 'http://localhost:8080/api/articles/generate' \
  -H 'Content-Type: application/json' \
  -d '{
    "category": "Spring Boot",
    "subcategory": "Spring Security",
    "tag": "JWT Authentication",
    "language": "es",
    "site": "https://mi-blog.com",
    "authorUsername": "juan",
    "avoidTitles": [
      "Introducción a JWT",
      "JWT para principiantes"
    ]
  }'
```

### Respuesta (recortada)

```json
{
  "title": "Autenticación JWT en Spring Boot 3: guía práctica",
  "slug": "autenticacion-jwt-en-spring-boot-3-guia-practica",
  "summary": "Aprende a implementar JWT en Spring Boot 3 con buenas prácticas.",
  "body": "<h1>Autenticación JWT en Spring Boot 3: guía práctica</h1>...",
  "category": "Spring Security",
  "tags": ["JWT Authentication"],
  "author": "juan",
  "status": "published",
  "isVisible": true,
  "keywords": ["jwt spring boot", "spring security", "token"],
  "metaTitle": "Autenticación JWT en Spring Boot 3: guía práctica",
  "metaDescription": "Aprende a implementar JWT en Spring Boot 3 con buenas prácticas.",
  "canonicalUrl": "https://mi-blog.com/post/autenticacion-jwt-en-spring-boot-3-guia-practica",
  "structuredData": {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "headline": "Autenticación JWT en Spring Boot 3: guía práctica",
    "description": "Aprende a implementar JWT en Spring Boot 3 con buenas prácticas.",
    "author": { "@type": "Person", "name": "juan" },
    "url": "https://mi-blog.com/post/autenticacion-jwt-en-spring-boot-3-guia-practica"
  },
  "ogTitle": "Autenticación JWT en Spring Boot 3: guía práctica",
  "ogDescription": "Aprende a implementar JWT en Spring Boot 3 con buenas prácticas.",
  "ogType": "article",
  "wordCount": 1300,
  "readingTime": 7,
  "publishDate": "2026-03-24T14:00:00Z",
  "createdAt": "2026-03-24T14:00:00Z",
  "updatedAt": "2026-03-24T14:00:00Z",
  "generatedAt": "2026-03-24T14:00:00Z"
}
```

---

## Modelo de entrada `ArticleRequest`

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `category` | `String` | ✅ Sí | Categoría del artículo |
| `subcategory` | `String` | No | Subcategoría (defecto: `"General"`) |
| `tag` | `String` | No | Etiqueta / tema del artículo |
| `title` | `String` | No | Título exacto a utilizar; si se proporciona, la IA genera el cuerpo alrededor de este título y se omite la deduplicación |
| `authorUsername` | `String` | No | Sobreescribe `article-generator.author-username` para esta petición |
| `site` | `String` | No | Sobreescribe `article-generator.site` para esta petición |
| `language` | `String` | No | Código ISO 639-1 (p.e. `es`, `en`); sobreescribe `article-generator.language` |
| `avoidTitles` | `List<String>` | No | Títulos a evitar en la deduplicación (solo se aplica cuando no se especifica `title`) |

---

## Modelo de respuesta `Article`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `title` | `String` | Título del artículo (optimizado para SEO) |
| `slug` | `String` | Slug URL-safe derivado del título |
| `summary` | `String` | Resumen/meta-descripción (≤ 160 caracteres recomendado) |
| `body` | `String` | Cuerpo completo del artículo en HTML semántico |
| `category` | `String` | Subcategoría del artículo |
| `tags` | `List<String>` | Etiquetas del artículo |
| `author` | `String` | Nombre de usuario del autor |
| `status` | `String` | Estado de publicación (siempre `"published"`) |
| `isVisible` | `boolean` | Visibilidad pública (siempre `true`) |
| `keywords` | `List<String>` | Palabras clave SEO de cola larga |
| `metaTitle` | `String` | Título para `<title>` (truncado a `meta-title-max-length`) |
| `metaDescription` | `String` | Meta-descripción (truncada a `meta-description-max-length`) |
| `canonicalUrl` | `String` | URL canónica: `{site}/post/{slug}` |
| `structuredData` | `Map<String, Object>` | Schema.org `TechArticle` JSON-LD para `<script type="application/ld+json">` |
| `ogTitle` | `String` | Título Open Graph |
| `ogDescription` | `String` | Descripción Open Graph |
| `ogType` | `String` | Tipo Open Graph (siempre `"article"`) |
| `wordCount` | `int` | Recuento aproximado de palabras del cuerpo |
| `readingTime` | `int` | Tiempo estimado de lectura en minutos |
| `publishDate` | `String` | Fecha de publicación ISO 8601 UTC |
| `createdAt` | `String` | Timestamp de creación ISO 8601 UTC |
| `updatedAt` | `String` | Timestamp de última modificación ISO 8601 UTC |
| `generatedAt` | `String` | Timestamp de generación ISO 8601 UTC |

---

## Notas rápidas

- Campo obligatorio en `ArticleRequest`: `category`.
- Si no envías `subcategory`, usa `General`.
- Si no envías `language`, `site` o `authorUsername`, se aplican los valores de `application.yml`.
- Si envías `title`, la IA genera el cuerpo del artículo alrededor de ese título exacto (se omite la deduplicación de fases).
- El starter aplica deduplicación de títulos usando `avoidTitles` (solo cuando no se especifica `title`).
- Todos los beans son `@ConditionalOnMissingBean`: el proyecto consumidor puede sobreescribir cualquiera.
