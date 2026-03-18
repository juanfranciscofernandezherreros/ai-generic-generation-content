# Cómo funciona `generateArticle.py`

Este documento explica en detalle la arquitectura interna, el flujo de datos y cada componente clave del script de publicación automática de artículos **optimizado para SEO**.

---

## Índice

1. [Visión general](#1-visión-general)
2. [Variables de entorno y configuración](#2-variables-de-entorno-y-configuración)
3. [Constantes importantes](#3-constantes-importantes)
4. [Arquitectura y componentes principales](#4-arquitectura-y-componentes-principales)
5. [Flujo de ejecución paso a paso](#5-flujo-de-ejecución-paso-a-paso)
6. [Funciones auxiliares (helpers)](#6-funciones-auxiliares-helpers)
7. [Gestión de categorías, subcategorías y tags](#7-gestión-de-categorías-subcategorías-y-tags)
8. [Integración con IA (OpenAI y Google Gemini)](#8-integración-con-ia-openai-y-google-gemini)
9. [Control del límite semanal](#9-control-del-límite-semanal)
10. [Sistema de notificaciones por correo](#10-sistema-de-notificaciones-por-correo)
11. [Documento JSON exportado](#11-documento-json-exportado)
12. [Diagrama de flujo](#12-diagrama-de-flujo)
13. [Optimización SEO completa](#13-optimización-seo-completa)

---

## 1. Visión general

`generateArticle.py` es un script Python que automatiza la **generación de artículos técnicos optimizados para SEO** y los exporta a un fichero JSON local. No requiere base de datos. El flujo principal es:

```
Argumentos CLI → Validación → IA (OpenAI/Gemini) → Metadatos SEO → Fichero JSON → Email
```

Cada ejecución genera **un artículo** a partir del tema indicado en `--tag`. El script está diseñado para ser ejecutado de forma programada (cron semanal, CI/CD, etc.) y notifica todos los eventos importantes por correo electrónico.

Cada artículo generado incluye:
- **Contenido HTML semántico** optimizado para SEO on-page (h1 > h2 > h3, FAQ, CTA)
- **Metadatos SEO**: `metaTitle` (≤ 60 chars), `metaDescription` (≤ 160 chars), `keywords` (5-7)
- **URL canónica** (`canonicalUrl`) para evitar contenido duplicado
- **Datos estructurados JSON-LD** (Schema.org `TechArticle`) para rich snippets
- **Metadatos Open Graph** (`ogTitle`, `ogDescription`, `ogType`) para redes sociales

---

## 2. Variables de entorno y configuración

El script carga su configuración desde un fichero `.env` en el mismo directorio (usando `python-dotenv`). Los argumentos CLI sobreescriben los valores del `.env`. Las variables disponibles son:

| Variable | Obligatoria | Descripción |
|---|---|---|
| `OPENAIAPIKEY` | ✅ (si modelo OpenAI) | Clave de API de OpenAI (`sk-...`) |
| `GEMINI_API_KEY` | ✅ (si modelo Gemini) | Clave de API de Google Gemini |
| `OPENAI_MODEL` | ❌ | Modelo a usar (por defecto `gpt-4o`). Si empieza por `gemini-`, usa Gemini |
| `AUTHOR_USERNAME` | ❌ | Nombre del autor de los artículos (por defecto `adminUser`) |
| `SITE` | ❌ | URL base de la web (ej. `https://tusitio.com`). Necesaria para URLs canónicas |
| `ARTICLE_LANGUAGE` | ❌ | Código ISO 639-1 del idioma (por defecto `es`) |
| `AI_TEMPERATURE_ARTICLE` | ❌ | Temperatura de generación del artículo (por defecto `0.7`) |
| `AI_TEMPERATURE_TITLE` | ❌ | Temperatura de generación del título (por defecto `0.9`) |
| `SMTP_HOST` | ❌ | Servidor SMTP para notificaciones |
| `SMTP_PORT` | ❌ | Puerto SMTP (por defecto `587`) |
| `SMTP_USER` | ❌ | Usuario SMTP |
| `SMTP_PASS` | ❌ | Contraseña SMTP |
| `FROM_EMAIL` | ❌ | Dirección de envío |
| `NOTIFY_EMAIL` | ❌ | Destinatario de las notificaciones |
| `NOTIFY_VERBOSE` | ❌ | Si es `true` (por defecto), envía email en cada evento; si es `false`, solo en errores/avisos |
| `LIMIT_PUBLICATION` | ❌ | Reservado para uso futuro. No afecta al comportamiento actual |
| `SEND_PROMPT_EMAIL` | ❌ | Si es `true`, envía por email el prompt antes de llamar a la IA |

### Argumentos CLI

El script acepta los siguientes argumentos CLI (todos sobreescriben las variables de entorno correspondientes):

| Argumento | Obligatorio | Por defecto | Descripción |
|---|---|---|---|
| `--tag` / `-t` | ✅ | — | Tema o tag del artículo |
| `--category` / `-c` | ❌ | `General` | Nombre de la categoría padre |
| `--subcategory` / `-s` | ❌ | `General` | Nombre de la subcategoría |
| `--output` / `-o` | ❌ | `article.json` | Ruta del fichero JSON de salida |
| `--username` / `--author` / `-u` / `-a` | ❌ | `AUTHOR_USERNAME` | Username/nombre del autor (`--author` y `-a` son alias para compatibilidad) |
| `--site` / `-S` | ❌ | `SITE` | URL base del sitio |
| `--language` / `-l` | ❌ | `ARTICLE_LANGUAGE` | Código de idioma ISO 639-1 |
| `--avoid-titles` | ❌ | `""` | Títulos a evitar, separados por `;` |

---

## 3. Constantes importantes

Definidas directamente en el código, controlan el comportamiento del algoritmo de deduplicación de títulos:

| Constante | Valor | Significado |
|---|---|---|
| `SIMILARITY_THRESHOLD_DEFAULT` | `0.82` | Umbral de similitud genérico: dos textos con ratio ≥ 0.82 se consideran "demasiado parecidos" |
| `SIMILARITY_THRESHOLD_STRICT` | `0.86` | Umbral más estricto que se aplica al reintentar la generación de un título |
| `MAX_TITLE_RETRIES` | `5` | Número máximo de intentos para obtener un título suficientemente único |
| `MAX_AVOID_TITLES_IN_PROMPT` | `5` | Máx. títulos a incluir en el prompt para evitar similitudes |
| `OPENAI_MAX_RETRIES` | `3` | Reintentos para errores transitorios de la API de OpenAI |
| `OPENAI_RETRY_BASE_DELAY` | `2` | Segundos base del back-off exponencial entre reintentos de OpenAI |
| `OPENAI_MAX_ARTICLE_TOKENS` | `4096` | Límite de tokens de salida para artículos |
| `OPENAI_MAX_TITLE_TOKENS` | `100` | Límite de tokens de salida para títulos |
| `META_TITLE_MAX_LENGTH` | `60` | Máx. caracteres para `metaTitle` |
| `META_DESCRIPTION_MAX_LENGTH` | `160` | Máx. caracteres para `metaDescription` |

---

## 4. Arquitectura y componentes principales

El script está organizado en capas bien separadas:

```
┌─────────────────────────────────────────────────────────────────┐
│  main()                                                          │
│  ├── Parseo de argumentos CLI (argparse)                         │
│  ├── Validación de entorno (clave API)                           │
│  └── generate_and_save_article()  ← generación y exportación    │
│       ├── generate_article_with_ai()  ← llamada a IA            │
│       ├── generate_title_with_ai()    ← reintentos de título     │
│       ├── build_json_ld_structured_data() ← SEO JSON-LD         │
│       └── json.dump(doc, file)        ← escritura en JSON       │
└─────────────────────────────────────────────────────────────────┘
```

### Módulos/grupos de funciones

| Grupo | Funciones clave | Responsabilidad |
|---|---|---|
| **Helpers genéricos** | `str_id`, `as_list`, `tag_name`, `slugify`, `html_escape` | Utilidades de conversión y normalización |
| **Similitud** | `normalize_for_similarity`, `similar_ratio`, `is_too_similar` | Detectar duplicados de título |
| **Notificaciones** | `send_notification_email`, `notify` | Email SMTP y logging unificado |
| **IA** | `build_generation_prompt`, `build_title_prompt`, `generate_article_with_ai`, `generate_title_with_ai`, `_generate_with_langchain` | Construir prompt SEO y parsear respuesta (LangChain + fallback directo) |
| **SEO** | `build_canonical_url`, `build_json_ld_structured_data` | URL canónica, datos estructurados JSON-LD (Schema.org) |
| **Publicación** | `generate_and_save_article` | Orquestar generación + deduplicación + SEO + exportación JSON |
| **Texto** | `extract_plain_text`, `count_words`, `estimate_reading_time` | Análisis del cuerpo HTML para métricas SEO |

---

## 5. Flujo de ejecución paso a paso

### Paso 1 — Parseo de argumentos CLI y validación de entorno

```python
# Argumentos CLI obligatorios y opcionales
parser.add_argument("--tag", required=True, ...)
parser.add_argument("--category", default="General", ...)
# ...
args = parser.parse_args()

# Comprueba que la clave de API está disponible
if not OPENAIAPIKEY and not GEMINI_API_KEY:
    notify("Configuración incompleta", ..., level="error")
    sys.exit(1)
```

Si falta la clave de API de IA (`OPENAIAPIKEY` o `GEMINI_API_KEY` según el modelo), se envía un email de error y el proceso se detiene inmediatamente.

---

### Paso 2 — Inicialización del cliente de IA

```python
if not using_gemini:
    client_ai = OpenAI(api_key=OPENAIAPIKEY)
else:
    # Gemini se usa a través de LangChain, no requiere cliente OpenAI
    client_ai = None
```

Inicializa el cliente OpenAI SDK (solo para fallback en modelos ChatGPT). Gemini se gestiona directamente a través de LangChain.

---

### Paso 3 — Generación del artículo con IA (SEO)

`generate_and_save_article(...)` orquesta la generación en dos fases:

```
Fase 1: Generar artículo completo (única llamada costosa)
  → generate_article_with_ai()  →  (title, summary, body, keywords)
  → Si el título es demasiado similar → Fase 2

Fase 2: Regenerar solo el título (llamadas ligeras, máx. 5 intentos)
  → generate_title_with_ai()  →  nuevo título
  → Si es único → actualizar <h1> del body y aceptar
```

Cada llamada a `generate_article_with_ai`:

1. Construye el prompt SEO con `build_generation_prompt` (incluye instrucciones detalladas de SEO on-page).
2. Intenta la llamada con **LangChain** (LCEL chain: `ChatOpenAI`/`ChatGoogleGenerativeAI` + `ChatPromptTemplate` + `StrOutputParser`).
3. Si falla, usa el **SDK de OpenAI Chat Completions** como fallback.
4. Extrae el bloque JSON de la respuesta con `_extract_json_block`.
5. Parsea el JSON con `_safe_json_loads` (tolerante a comillas tipográficas).
6. Devuelve `(title, summary, body, keywords)`.

---

### Paso 4 — Generación de metadatos SEO y exportación a JSON

Si el título es único, se generan todos los metadatos SEO y se exporta el documento:

```python
# Métricas del contenido
word_count = count_words(body)
reading_time = estimate_reading_time(body)

# Metadatos SEO
meta_title = title[:60]
meta_description = summary[:160]
canonical_url = build_canonical_url(site, slug)
structured_data = build_json_ld_structured_data(...)  # JSON-LD Schema.org

doc = {
    "title": title, "slug": slug, "summary": summary, "body": body,
    "category": subcat_name, "tags": [tag_text],
    "author": author_name, "status": "published",
    "metaTitle": meta_title, "metaDescription": meta_description,
    "canonicalUrl": canonical_url, "structuredData": structured_data,
    "ogTitle": meta_title, "ogDescription": meta_description, "ogType": "article",
    "wordCount": word_count, "readingTime": reading_time, "keywords": keywords,
    "publishDate": now_iso, "createdAt": now_iso, ...
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
```

El **slug** se genera con `slugify(title)`.

---

### Paso 5 — Notificación y fin

- Si se generó: email de éxito con título, slug y tag. Imprime ruta del fichero JSON.
- Si no se generó (todos los intentos de título fallaron): email de aviso.
- En ambos casos, imprime el resumen final en consola.

---

## 6. Funciones auxiliares (helpers)

### `slugify(text: str) → str`

Convierte un texto en un slug URL-friendly:

1. Normaliza caracteres Unicode (NFD) y elimina diacríticos (acentos).
2. Pasa a minúsculas.
3. Sustituye cualquier carácter no alfanumérico por `-`.
4. Elimina guiones al inicio y al final.

```python
slugify("Cómo usar @Builder en Spring Boot")
# → "como-usar-builder-en-spring-boot"
```

### `is_too_similar(title, candidates, threshold) → bool`

Usa `difflib.SequenceMatcher` sobre versiones normalizadas (sin acentos, minúsculas, sin signos de puntuación) de los títulos. Devuelve `True` si la ratio de similitud con cualquier candidato supera el umbral.

### `html_escape(s) → str`

Escapa `&`, `<` y `>` para uso seguro en correos HTML. Evita que el contenido del artículo rompa el HTML del email.

---

## 7. Gestión de categorías, subcategorías y tags

Esta sección describe la taxonomía de temas disponibles y cómo el script la utiliza para organizar el contenido generado.

---

### 7.1 Estructura jerárquica

La taxonomía tiene **tres niveles**, definida en `seed_data.py` como la constante `TAXONOMY`:

```
┌─────────────────────────────────────────────────────────────────────┐
│  NIVEL 1 — Categoría padre                                          │
│  ej. "Spring Boot" / "Data & Persistencia" / "Inteligencia         │
│       Artificial"                                                   │
│                                                                     │
│   └── NIVEL 2 — Subcategoría                                        │
│       ej. "Lombok" / "Spring Security" / "Spring AI"               │
│                                                                     │
│         └── NIVEL 3 — Tag                                           │
│             ej. "@Data" / "JWT Authentication" / "Spring AI         │
│                  Overview"                                          │
└─────────────────────────────────────────────────────────────────────┘
```

Cada artículo generado se asocia a una **categoría** (campo `category`), uno o más **tags** (campo `tags`) y un **autor** (campo `author`) en el JSON de salida.

---

### 7.2 Taxonomía predefinida (`seed_data.py`)

El fichero `seed_data.py` define la constante `TAXONOMY` con la siguiente estructura (3 categorías padre, 14 subcategorías y ~140 tags):

```
Spring Boot (categoría padre)
├── Spring Boot Core         → 10 tags  (@SpringBootApplication, Auto-configuration, ...)
├── Spring Security          → 10 tags  (JWT Authentication, OAuth2, ...)
├── Spring Data JPA          → 10 tags  (@Entity y @Table, JpaRepository, ...)
├── Spring MVC REST          → 10 tags  (@RestController, ResponseEntity, ...)
├── Spring Boot Testing      → 10 tags  (@SpringBootTest, @WebMvcTest, ...)
└── Lombok                   → 10 tags  (@Data, @Builder, @Slf4j, ...)

Data & Persistencia (categoría padre)
├── JPA e Hibernate          → 10 tags  (Hibernate Caching L1 y L2, N+1, ...)
├── Bases de Datos SQL        → 10 tags  (PostgreSQL, MySQL, Flyway, ...)
├── NoSQL y MongoDB          → 10 tags  (Spring Data MongoDB, @Document, ...)
└── Migraciones de Esquema   →  8 tags  (Flyway, Liquibase, Rollback, ...)

Inteligencia Artificial (categoría padre)
├── Spring AI                → 10 tags  (Spring AI Overview, ChatClient, ...)
├── LLMs y Modelos de Lenguaje→ 10 tags  (OpenAI API con Java, GPT-4, ...)
├── Machine Learning con Java→ 10 tags  (Deeplearning4j, TensorFlow Java, ...)
└── Vector Databases y RAG   → 10 tags  (Embeddings, RAG, Pinecone, ...)
```

Puedes usar cualquier tag de esta taxonomía como valor del argumento `--tag` al ejecutar el script. También puedes generar artículos sobre temas completamente distintos pasando cualquier texto en `--tag`.

---

### 7.3 Rol SEO de la jerarquía

La estructura de tres niveles no solo organiza el contenido, sino que refuerza el SEO:

| Nivel | Rol SEO |
|---|---|
| **Categoría padre** | Define el **silo temático** (cluster de contenido). Los buscadores premian sitios con contenido agrupado temáticamente. |
| **Subcategoría** | Define el **campo `articleSection`** en los datos estructurados y la clasificación del artículo. |
| **Tag** | Define la **palabra clave principal** del artículo. Es la semilla del prompt que genera el contenido. |

---

## 8. Integración con IA (OpenAI y Google Gemini)

### Proveedor de IA

El script soporta dos proveedores de IA según el valor de `OPENAI_MODEL`:

| Modelo | Proveedor | Variable de API |
|---|---|---|
| `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`, etc. | OpenAI | `OPENAIAPIKEY` |
| `gemini-1.5-pro`, `gemini-2.0-flash`, etc. | Google Gemini | `GEMINI_API_KEY` |

### System message (contexto del modelo)

El modelo recibe un system message que lo configura como **experto en SEO técnico y redacción**:

```python
GENERATION_SYSTEM_MSG = (
    "Eres redactor técnico sénior y experto en SEO especializado en tecnología y desarrollo de software. "
    "Generas contenido optimizado para motores de búsqueda con HTML semántico, "
    "estructura de encabezados jerárquica (h1 > h2 > h3), uso estratégico de palabras clave "
    "y metadatos precisos. "
    "Devuelves SOLO JSON válido con: title, summary, body (HTML semántico), keywords."
)
```

### Prompt de generación (SEO on-page)

`build_generation_prompt(parent_name, subcat_name, tag_text, avoid_titles, language)` produce un prompt en el idioma indicado con instrucciones SEO detalladas que instruye al modelo a devolver **únicamente un JSON** con la estructura:

```json
{
  "title":    "...",
  "summary":  "...",
  "body":     "...",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}
```

| Campo | Descripción | Restricción |
|---|---|---|
| `title` | Título del artículo, optimizado para SEO y CTR, con keyword principal al inicio | máx. 60 caracteres |
| `summary` | Meta descripción SEO con keyword y llamada a la acción implícita | máx. 160 caracteres |
| `body` | Cuerpo completo en HTML semántico con `<h1>`, secciones `<h2>`, `<h3>`, `<pre><code>`, `<strong>`, `<em>`, FAQ con preguntas reales y conclusión con CTA | — |
| `keywords` | Lista de 5-7 palabras clave SEO en minúsculas, incluyendo variaciones long-tail | sin repetir el título exacto |

### Estrategia de llamada con fallback (LangChain + SDK directo)

El script intenta en este orden:

```
1. LangChain LCEL chain:
   ChatOpenAI / ChatGoogleGenerativeAI
   + ChatPromptTemplate
   + StrOutputParser
   → _generate_with_langchain()
   Si falla (error de red, timeout, etc.) →

2. OpenAI SDK directo (solo para modelos OpenAI):
   client.chat.completions.create(model, messages)
   → Chat Completions — endpoint estándar
```

Ambas rutas tienen reintentos con **back-off exponencial** para errores transitorios (`ConnectionError`, `TimeoutError`).

### Parseo tolerante de la respuesta

La respuesta puede llegar en distintos formatos:
- JSON puro.
- Bloque de código ```json … ```.
- Texto con JSON embebido.

`_extract_json_block` extrae el primer objeto JSON válido. `_safe_json_loads` tolera comillas tipográficas (`"`, `"`) que a veces produce el modelo.

---

## 9. Control del límite semanal

```python
def current_week_window_utc_for_madrid(start_weekday=1):
    tz_madrid = ZoneInfo("Europe/Madrid")
    today = datetime.now(tz_madrid).date()
    # Calcula el lunes de la semana actual
    delta_days = (today.isoweekday() - start_weekday) % 7
    start_local = datetime.combine(today - timedelta(days=delta_days), time(0,0), tzinfo=tz_madrid)
    end_local = start_local + timedelta(days=7)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
```

Esta función se usa internamente para calcular ventanas de tiempo en hora de Madrid, independientemente del huso horario del servidor.

La variable `LIMIT_PUBLICATION` está reservada para uso futuro.

---

## 10. Sistema de notificaciones por correo

`notify(subject, message, level, always_email)` centraliza todo el logging:

1. Imprime en consola con timestamp UTC y emoji indicador de nivel.
2. Decide si enviar email según:
   - `always_email=True` → siempre envía.
   - `NOTIFY_VERBOSE=true` → envía en todos los eventos.
   - `level in ("error","warning")` → siempre envía errores y advertencias.

Los niveles disponibles son: `info`, `success`, `warning`, `error`.

`send_notification_email` envía un email SMTP con **texto plano + alternativa HTML** usando la librería estándar `smtplib` y `email.message.EmailMessage`. La conexión usa STARTTLS.

---

## 11. Documento JSON exportado

El artículo exportado al fichero JSON tiene la siguiente estructura:

```json
{
  "title":           "Cómo usar @Data en Lombok",
  "slug":            "como-usar-data-en-lombok",
  "summary":         "Resumen del artículo...",
  "body":            "<h1>...</h1><p>...</p>...",
  "category":        "Lombok",
  "tags":            ["@Data"],
  "author":          "adminUser",
  "status":          "published",
  "likes":           [],
  "favoritedBy":     [],
  "isVisible":       true,
  "publishDate":     "2025-06-15T08:00:00+00:00",
  "generatedAt":     "2025-06-15T08:00:00+00:00",
  "createdAt":       "2025-06-15T08:00:00+00:00",
  "updatedAt":       "2025-06-15T08:00:00+00:00",
  "images":          null,
  "wordCount":       1240,
  "readingTime":     6,
  "keywords":        ["lombok", "@data", "java", "boilerplate", "pojo"],
  "metaTitle":       "Cómo usar @Data en Lombok",
  "metaDescription": "Aprende a reducir el código boilerplate con @Data de Lombok en Spring Boot.",
  "canonicalUrl":    "https://tusitio.com/post/como-usar-data-en-lombok",
  "ogTitle":         "Cómo usar @Data en Lombok",
  "ogDescription":   "Aprende a reducir el código boilerplate con @Data de Lombok en Spring Boot.",
  "ogType":          "article",
  "structuredData":  {
    "@context": "https://schema.org",
    "@type": "TechArticle",
    "headline": "Cómo usar @Data en Lombok",
    "description": "Aprende a reducir el código boilerplate con @Data de Lombok.",
    "author": { "@type": "Person", "name": "adminUser" },
    "publisher": { "@type": "Organization", "name": "tusitio.com", "url": "https://tusitio.com" },
    "datePublished": "2025-06-15T08:00:00+00:00",
    "dateModified": "2025-06-15T08:00:00+00:00",
    "url": "https://tusitio.com/post/como-usar-data-en-lombok",
    "mainEntityOfPage": { "@type": "WebPage", "@id": "https://tusitio.com/post/como-usar-data-en-lombok" },
    "wordCount": 1240,
    "timeRequired": "PT6M",
    "inLanguage": "es",
    "keywords": "lombok, @data, java, boilerplate, pojo",
    "articleSection": "Lombok",
    "about": [{ "@type": "Thing", "name": "@Data" }]
  }
}
```

### Campos de contenido

| Campo | Tipo | Descripción |
|---|---|---|
| `title` | `string` | Título del artículo generado por la IA. |
| `slug` | `string` | Versión URL-friendly del título (sin acentos, minúsculas, guiones). |
| `summary` | `string` | Resumen corto del artículo (meta descripción). |
| `body` | `string` | Cuerpo completo del artículo en HTML semántico. |
| `category` | `string` | Nombre de la subcategoría (o categoría) indicada con `--subcategory`. |
| `tags` | `[string]` | Lista de tags. Contiene el valor de `--tag`. |
| `author` | `string` | Nombre/username del autor (valor de `--username` / `--author`). |
| `status` | `string` | Estado del artículo (`published`). |

### Campos SEO

| Campo | Tipo | Límite | Descripción |
|---|---|---|---|
| `metaTitle` | `string` | ≤ 60 chars | Título SEO optimizado. Para la etiqueta `<title>` de la página. |
| `metaDescription` | `string` | ≤ 160 chars | Meta descripción SEO. Para `<meta name="description">`. |
| `canonicalUrl` | `string` | — | URL canónica completa (`{SITE}/post/{slug}`). Para `<link rel="canonical">`. |
| `keywords` | `[string]` | 5-7 items | Palabras clave SEO en minúsculas. Para `<meta name="keywords">`. |
| `ogTitle` | `string` | ≤ 60 chars | Título Open Graph. Para `<meta property="og:title">`. |
| `ogDescription` | `string` | ≤ 160 chars | Descripción Open Graph. Para `<meta property="og:description">`. |
| `ogType` | `string` | — | Tipo Open Graph (`article`). Para `<meta property="og:type">`. |
| `structuredData` | `object` | — | JSON-LD Schema.org `TechArticle`. Para `<script type="application/ld+json">`. |

### Campos de métricas

| Campo | Tipo | Descripción |
|---|---|---|
| `wordCount` | `int` | Número de palabras del cuerpo HTML (texto plano). |
| `readingTime` | `int` | Tiempo de lectura estimado en minutos (`ceil(wordCount / 230)`), mínimo 1. |

### Campos de fechas

| Campo | Tipo | Descripción |
|---|---|---|
| `publishDate` | `string` (ISO 8601) | Fecha y hora de publicación (UTC). |
| `generatedAt` | `string` (ISO 8601) | Fecha y hora de generación (UTC). |
| `createdAt` | `string` (ISO 8601) | Fecha de creación del documento (UTC). |
| `updatedAt` | `string` (ISO 8601) | Fecha de última actualización (UTC). |

> Todas las fechas se almacenan en **UTC** en formato ISO 8601.

---

## 12. Diagrama de flujo

### 12.1 Flujo principal del script

```
┌─────────────────────────────────────────┐
│             INICIO (main)               │
└────────────────┬────────────────────────┘
                 │
        ┌────────▼────────┐
        │ Parsear args CLI │
        │ --tag, --category│
        │ --subcategory, ..│
        └────────┬────────┘
                 │
        ┌────────▼──────────┐
        │ ¿Clave API OK?    │──── NO ──► Email error + sys.exit(1)
        └────────┬──────────┘
                 │ SÍ
        ┌────────▼──────────────────────────────────────┐
        │ generate_and_save_article()                    │
        │  ┌──────────────────────────────────────────┐ │
        │  │  Fase 1: generate_article_with_ai()      │ │
        │  │   1. build_generation_prompt()           │ │
        │  │   2. LangChain chain (primario)          │ │
        │  │   3. OpenAI SDK fallback (si falla)      │ │
        │  │   4. _extract_json_block + _safe_json    │ │
        │  │   → (title, summary, body, keywords)     │ │
        │  │                                          │ │
        │  │  ¿Título demasiado similar?              │ │
        │  │   SÍ → Fase 2: generate_title_with_ai() │ │
        │  │         (máx. 5 intentos)                │ │
        │  │   NO → aceptar título                    │ │
        │  └──────────────────────────────────────────┘ │
        │  ¿Título obtenido?                             │
        └────────┬───────────────────┬──────────────────┘
                 │ SÍ                │ NO
        ┌────────▼──────┐   ┌────────▼──────────────────┐
        │ Generar SEO   │   │ Email error (sin título)   │
        │ Exportar JSON │   └───────────────────────────┘
        │ Email éxito   │
        └────────┬───────┘
                 │
        ┌────────▼──────────────────┐
        │ FIN — Email "Proceso OK"  │
        └───────────────────────────┘
```

---

### 12.2 Diagrama detallado: Pipeline de generación

```
  seed_data.py                    generateArticle.py (CLI)
  ─────────────                   ─────────────────────────────

  TAXONOMY[]                      args: --tag, --category, --subcategory
     │                                    │
     │  (referencia de temas              │
     │   disponibles)                     ▼
     │                        generate_and_save_article(
     │                            tag_text, parent_name, subcat_name, ...)
     │                                    │
     │                                    ├─ build_generation_prompt()
     │                                    │   → Prompt SEO con instrucciones
     │                                    │
     │                                    ├─ generate_article_with_ai()
     │                                    │   → LangChain (primario)
     │                                    │   → OpenAI SDK (fallback)
     │                                    │   → (title, summary, body, keywords)
     │                                    │
     │                                    ├─ is_too_similar()?
     │                                    │   SÍ → generate_title_with_ai()
     │                                    │         (máx. MAX_TITLE_RETRIES)
     │                                    │
     │                                    ├─ slugify(title)
     │                                    ├─ count_words(body)
     │                                    ├─ estimate_reading_time()
     │                                    ├─ build_canonical_url()
     │                                    ├─ build_json_ld_structured_data()
     │                                    │
     │                                    ▼
     │                               json.dump(doc)
     │                               → article.json  (fichero de salida)
```

---

## 13. Optimización SEO completa

Esta sección documenta todas las funcionalidades SEO del sistema, cómo se generan y cómo se relacionan con las categorías, subcategorías y tags.

---

### 13.1 Pipeline SEO del artículo

El flujo completo de generación SEO sigue estos pasos:

```
Tag (--tag, keyword principal)
    │
    ▼
build_generation_prompt()
    │  → Prompt SEO con instrucciones de:
    │    · Título SEO ≤60 chars con keyword al inicio
    │    · Meta descripción ≤160 chars con CTA
    │    · 5-7 keywords long-tail
    │    · HTML semántico (h1 > h2 > h3)
    │    · <strong>/<em> para énfasis
    │    · FAQ con preguntas reales
    │    · Conclusión con CTA
    │
    ▼
generate_article_with_ai()
    │  → (title, summary, body, keywords)
    │
    ▼
generate_and_save_article()  ← orquestador principal
    │
    ├─ slugify(title)          → slug SEO-friendly
    ├─ count_words(body)       → wordCount
    ├─ estimate_reading_time() → readingTime
    ├─ metaTitle               → title[:60]
    ├─ metaDescription         → summary[:160]
    ├─ build_canonical_url()   → canonicalUrl
    ├─ build_json_ld_structured_data()  → structuredData
    ├─ ogTitle, ogDescription, ogType   → Open Graph
    │
    ▼
json.dump(doc, output_file)
    → Fichero JSON con TODOS los campos SEO
```

---

### 13.2 Funciones SEO en detalle

#### `build_canonical_url(site: str, slug: str) → str`

Construye la URL canónica del artículo:

```python
build_canonical_url("https://tusitio.com", "como-usar-data-en-lombok")
# → "https://tusitio.com/post/como-usar-data-en-lombok"
```

- Si `site` o `slug` están vacíos, devuelve `""`.
- Elimina barras finales del dominio para evitar duplicados.
- Se usa para la etiqueta `<link rel="canonical">` y en los datos estructurados.

#### `build_json_ld_structured_data(...) → dict`

Genera un diccionario con datos estructurados JSON-LD siguiendo el vocabulario [Schema.org](https://schema.org/TechArticle). Campos incluidos:

| Campo Schema.org | Valor | Origen |
|---|---|---|
| `@type` | `TechArticle` | Fijo (artículos técnicos) |
| `headline` | Título (≤ 110 chars) | `title` del artículo |
| `description` | Resumen (≤ 200 chars) | `summary` del artículo |
| `author` | `{ @type: Person, name: ... }` | `--username` / `--author` / `AUTHOR_USERNAME` |
| `publisher` | `{ @type: Organization, name: ..., url: ... }` | `--site` / `SITE` |
| `datePublished` | ISO 8601 | Fecha de publicación |
| `dateModified` | ISO 8601 | Fecha de modificación |
| `url` | URL canónica | `canonicalUrl` |
| `mainEntityOfPage` | `{ @type: WebPage, @id: ... }` | `canonicalUrl` |
| `wordCount` | Número entero | `count_words(body)` |
| `timeRequired` | `PT{n}M` (ISO 8601 duration) | `estimate_reading_time(body)` |
| `inLanguage` | código ISO (ej. `es`) | `--language` / `ARTICLE_LANGUAGE` |
| `keywords` | String separado por comas | `keywords` del artículo |
| `articleSection` | Nombre de la subcategoría | `--subcategory` |
| `about` | `[{ @type: Thing, name: ... }]` | `--tag` |

---

### 13.3 Relación SEO ↔ Categorías, Subcategorías y Tags

La jerarquía de tres niveles tiene un papel directo en la estrategia SEO:

```
┌──────────────────────────────────────────────────────────────────────┐
│  CATEGORÍA PADRE (Silo temático / Content cluster)                   │
│  ej. "Spring Boot"  →  pasado con --category                        │
│                                                                      │
│  ROL SEO:                                                            │
│  · Define el cluster de contenido (topic cluster)                   │
│  · Los artículos dentro del mismo silo se refuerzan mutuamente      │
│  · Mejora la autoridad temática (topical authority) del sitio       │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  SUBCATEGORÍA (Sección del artículo / Article section)        │  │
│  │  ej. "Lombok"  →  pasado con --subcategory                    │  │
│  │                                                                │  │
│  │  ROL SEO:                                                      │  │
│  │  · Campo `articleSection` en datos estructurados               │  │
│  │  · Campo `category` en el JSON exportado                       │  │
│  │  · Permite navegación facetada en el frontend                  │  │
│  │                                                                │  │
│  │  ┌──────────────────────────────────────────────────────────┐ │  │
│  │  │  TAG (Palabra clave principal / Primary keyword)         │ │  │
│  │  │  ej. "@Data"  →  pasado con --tag                        │ │  │
│  │  │                                                           │ │  │
│  │  │  ROL SEO:                                                 │ │  │
│  │  │  · Semilla del prompt → keyword principal del artículo   │ │  │
│  │  │  · Incluida en el título (al inicio para SEO)            │ │  │
│  │  │  · Incluida en la meta descripción                       │ │  │
│  │  │  · Incluida en el <h1> del body                          │ │  │
│  │  │  · Campo `about` en datos estructurados                  │ │  │
│  │  │  · Campo `tags` en el JSON exportado                     │ │  │
│  │  └──────────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 13.4 Instrucciones SEO en el prompt de generación

El prompt enviado a la IA incluye las siguientes directivas SEO:

| Directiva | Objetivo SEO |
|---|---|
| "título optimizado para SEO y CTR" | Maximizar clics en resultados de búsqueda |
| "palabra clave principal al inicio" | Mejora relevancia en SERPs |
| "máx. 60 caracteres" | Evitar truncamiento en Google |
| "meta-descripción SEO, máx. 160 chars" | Snippet completo en resultados |
| "llamada a la acción implícita" | Mejorar CTR del snippet |
| "5-7 keywords long-tail" | Capturar tráfico de cola larga |
| "HTML semántico" | Facilitar interpretación por crawlers |
| "h1 > h2 > h3 jerárquico" | Estructura de encabezados correcta |
| "`<strong>` y `<em>` para términos clave" | Señal de importancia para buscadores |
| "FAQ con preguntas como búsquedas reales" | Aparecer en "People also ask" de Google |
| "Conclusión con CTA" | Reducir tasa de rebote, mejorar engagement |
| "Párrafos cortos (3-4 líneas)" | Mejorar legibilidad y Core Web Vitals |
| "Código en `<pre><code>`" | Rich snippets de código |

---

### 13.5 Cómo usar los campos SEO en tu frontend

Para que los artículos generados se beneficien del SEO completo, tu frontend debe renderizar los metadatos almacenados:

```html
<head>
  <!-- SEO básico -->
  <title>{{ article.metaTitle }}</title>
  <meta name="description" content="{{ article.metaDescription }}">
  <meta name="keywords" content="{{ article.keywords | join(', ') }}">
  <link rel="canonical" href="{{ article.canonicalUrl }}">

  <!-- Open Graph (redes sociales) -->
  <meta property="og:title" content="{{ article.ogTitle }}">
  <meta property="og:description" content="{{ article.ogDescription }}">
  <meta property="og:type" content="{{ article.ogType }}">
  <meta property="og:url" content="{{ article.canonicalUrl }}">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{{ article.ogTitle }}">
  <meta name="twitter:description" content="{{ article.ogDescription }}">

  <!-- Datos estructurados JSON-LD -->
  <script type="application/ld+json">
    {{ article.structuredData | json }}
  </script>
</head>
```

---

### 13.6 Métricas SEO generadas automáticamente

| Métrica | Función | Uso en frontend |
|---|---|---|
| `wordCount` | `count_words(body)` | Mostrar "1240 palabras" en el artículo. Señal de contenido extenso para Google. |
| `readingTime` | `estimate_reading_time(body, wpm=230)` | Mostrar "6 min de lectura". Mejora UX y engagement. |
| `metaTitle` | `title[:60]` | Etiqueta `<title>`. |
| `metaDescription` | `summary[:160]` | Etiqueta `<meta description>`. |
| `canonicalUrl` | `build_canonical_url(site, slug)` | Etiqueta `<link rel="canonical">`. |
