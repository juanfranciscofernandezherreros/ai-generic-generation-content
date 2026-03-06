# Cómo funciona `generateArticle.py`

Este documento explica en detalle la arquitectura interna, el flujo de datos y cada componente clave del script de publicación automática de artículos.

---

## Índice

1. [Visión general](#1-visión-general)
2. [Variables de entorno y configuración](#2-variables-de-entorno-y-configuración)
3. [Constantes importantes](#3-constantes-importantes)
4. [Arquitectura y componentes principales](#4-arquitectura-y-componentes-principales)
5. [Flujo de ejecución paso a paso](#5-flujo-de-ejecución-paso-a-paso)
6. [Funciones auxiliares (helpers)](#6-funciones-auxiliares-helpers)
7. [Gestión de categorías, subcategorías y tags](#7-gestión-de-categorías-subcategorías-y-tags)
8. [Integración con OpenAI](#8-integración-con-openai)
9. [Control del límite semanal](#9-control-del-límite-semanal)
10. [Sistema de notificaciones por correo](#10-sistema-de-notificaciones-por-correo)
11. [Documento insertado en MongoDB](#11-documento-insertado-en-mongodb)
12. [Diagrama de flujo](#12-diagrama-de-flujo)

---

## 1. Visión general

`generateArticle.py` es un script Python que automatiza la **generación y publicación semanal de artículos técnicos** en una base de datos MongoDB. El flujo principal es:

```
Configuración → MongoDB → Límite semanal → Elegir tema → IA (OpenAI) → Guardar artículo → Email
```

Cada ejecución publica **como máximo un artículo** (por defecto). El script está diseñado para ser ejecutado de forma programada (cron semanal, CI/CD, etc.) y notifica todos los eventos importantes por correo electrónico.

---

## 2. Variables de entorno y configuración

El script carga su configuración desde un fichero `.env` en el mismo directorio (usando `python-dotenv`). Las variables disponibles son:

| Variable | Obligatoria | Descripción |
|---|---|---|
| `MONGODB_URI` | ✅ | URI de conexión a MongoDB (ej. `mongodb://admin:pass@localhost:27017/blogdb?authSource=admin`) |
| `DB_NAME` | ✅ | Nombre de la base de datos |
| `CATEGORY_COLL` | ✅ | Nombre de la colección de categorías |
| `TAGS_COLL` | ✅ | Nombre de la colección de tags |
| `USERS_COLL` | ✅ | Nombre de la colección de usuarios |
| `ARTICLES_COLL` | ✅ | Nombre de la colección de artículos |
| `OPENAIAPIKEY` | ✅ | Clave de API de OpenAI (`sk-...`) |
| `OPENAI_MODEL` | ❌ | Modelo a usar (por defecto `gpt-5`) |
| `AUTHOR_USERNAME` | ❌ | Usuario autor de los artículos (por defecto `adminUser`) |
| `SITE` | ❌ | URL base de la web (ej. `https://tusitio.com`) |
| `SMTP_HOST` | ❌ | Servidor SMTP para notificaciones |
| `SMTP_PORT` | ❌ | Puerto SMTP (por defecto `587`) |
| `SMTP_USER` | ❌ | Usuario SMTP |
| `SMTP_PASS` | ❌ | Contraseña SMTP |
| `FROM_EMAIL` | ❌ | Dirección de envío |
| `NOTIFY_EMAIL` | ❌ | Destinatario de las notificaciones |
| `NOTIFY_VERBOSE` | ❌ | Si es `true` (por defecto), envía email en cada evento; si es `false`, solo en errores/avisos |
| `LIMIT_PUBLICATION` | ❌ | Si es `true` (por defecto), limita a 1 artículo por semana |
| `SEND_PROMPT_EMAIL` | ❌ | Si es `true`, envía por email el prompt antes de llamar a OpenAI |

> Las variables sin un valor predeterminado que sean obligatorias harán que el script se detenga con `sys.exit(1)` si faltan.

---

## 3. Constantes importantes

Definidas directamente en el código, controlan el comportamiento del algoritmo de deduplicación de títulos:

| Constante | Valor | Significado |
|---|---|---|
| `SIMILARITY_THRESHOLD_DEFAULT` | `0.82` | Umbral de similitud genérico: dos textos con ratio ≥ 0.82 se consideran "demasiado parecidos" |
| `SIMILARITY_THRESHOLD_STRICT` | `0.86` | Umbral más estricto que se aplica al reintentar la generación de un título |
| `MAX_TITLE_RETRIES` | `5` | Número máximo de intentos para obtener un título suficientemente único |
| `RECENT_TITLES_LIMIT` | `50` | Cuántos títulos recientes se cargan de MongoDB para la comparación |
| `OPENAI_MAX_RETRIES` | `3` | Reintentos para errores transitorios de la API de OpenAI |
| `OPENAI_RETRY_BASE_DELAY` | `2` | Segundos base del back-off exponencial entre reintentos de OpenAI |
| `MONGO_TIMEOUT_MS` | `5000` | Tiempo máximo de espera para la selección de servidor MongoDB |

---

## 4. Arquitectura y componentes principales

El script está organizado en capas bien separadas:

```
┌─────────────────────────────────────────────────────────────────┐
│  main()                                                          │
│  ├── Validación de entorno                                       │
│  ├── Conexión MongoDB                                            │
│  ├── Control límite semanal                                      │
│  ├── Carga de datos (categorías, tags, autor)                    │
│  ├── pick_fresh_target_strict()  ← selección de tema            │
│  └── ensure_article_for_tag()   ← generación e inserción        │
│       ├── generate_article_with_ai()  ← llamada a OpenAI        │
│       └── db.insert_one()             ← escritura en MongoDB    │
└─────────────────────────────────────────────────────────────────┘
```

### Módulos/grupos de funciones

| Grupo | Funciones clave | Responsabilidad |
|---|---|---|
| **Helpers genéricos** | `str_id`, `as_list`, `tag_name`, `slugify`, `html_escape` | Utilidades de conversión y normalización |
| **Similitud** | `normalize_for_similarity`, `similar_ratio`, `is_too_similar` | Detectar duplicados de título |
| **Notificaciones** | `send_notification_email`, `notify` | Email SMTP y logging unificado |
| **MongoDB (batch)** | `preload_published_tag_ids`, `preload_published_category_ids` | Evitar consultas N+1 |
| **Jerarquía** | `build_hierarchy`, `index_tags`, `find_subcats_with_tags` | Árbol categorías/subcategorías/tags |
| **Selección** | `pick_fresh_target_strict`, `guess_parent_and_subcat_for_tag` | Elegir el tema con regla estricta |
| **IA** | `build_generation_prompt`, `generate_article_with_ai`, `_extract_json_block`, `_safe_json_loads` | Construir prompt y parsear respuesta |
| **Publicación** | `ensure_article_for_tag` | Orquestar generación + deduplicación + inserción |
| **Tiempo** | `current_week_window_utc_for_madrid`, `today_window_utc_for_madrid` | Calcular ventana semanal en zona horaria de Madrid |

---

## 5. Flujo de ejecución paso a paso

### Paso 1 — Validación de entorno

```python
# Comprueba que todas las variables obligatorias están definidas
if missing:
    notify("Configuración incompleta", ..., level="error")
    sys.exit(1)
```

Si falta cualquier variable crítica (`OPENAIAPIKEY`, `MONGODB_URI`, etc.), se envía un email de error y el proceso se detiene inmediatamente.

---

### Paso 2 — Conexión a MongoDB

```python
client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
```

Abre la conexión con un timeout de 5 segundos. Si falla, notifica el error y termina.

---

### Paso 3 — Control del límite semanal

Si `LIMIT_PUBLICATION=true` (por defecto):

1. Calcula la ventana lunes-domingo de la semana actual en hora de Madrid.
2. Busca en MongoDB artículos con `status: "published"` cuya `publishDate` caiga dentro de esa ventana.
3. Si ya hay **1 o más**, notifica con los detalles del artículo ya publicado y termina con `sys.exit(0)`.

```python
already_this_week = db[ARTICLES_COLL].count_documents({
    "publishDate": {"$gte": start_utc, "$lt": end_utc},
    "status": "published"
})
```

---

### Paso 4 — Carga de datos

```python
categories = list(db[CATEGORY_COLL].find({}))
tags       = list(db[TAGS_COLL].find({}))
author_id  = find_author_id(db)
```

- Carga todas las categorías y tags en memoria (colecciones pequeñas).
- Busca el usuario autor por `username`, `userName` o `name` (insensible a mayúsculas).

---

### Paso 5 — Pre-carga de cobertura (optimización N+1)

```python
published_tag_ids = preload_published_tag_ids(db)
published_cat_ids = preload_published_category_ids(db)
```

En lugar de hacer una consulta a MongoDB por cada tag o categoría (N+1), se ejecutan **dos agregaciones** que devuelven el conjunto completo de IDs ya cubiertos. Esto se pasa a `pick_fresh_target_strict` para comparaciones O(1).

---

### Paso 6 — Selección estricta del tema

`pick_fresh_target_strict(...)` devuelve una tupla `(parent, subcat, tag)` eligiendo aleatoriamente entre los candidatos que cumplan:

- El **tag** no tiene ningún artículo publicado.
- La **subcategoría** no tiene ningún artículo publicado.
- La **categoría padre** no tiene ningún artículo publicado.

Si no hay candidatos con tag disponible, intenta elegir una categoría/subcategoría sin artículos (publicación sin tag). Si todo está cubierto, notifica y termina.

---

### Paso 7 — Generación del artículo con IA

`ensure_article_for_tag(...)` orquesta el bucle de generación con hasta `MAX_TITLE_RETRIES` intentos:

```
bucle:
  1. Llamar a generate_article_with_ai()  →  (title, summary, body)
  2. Si el título es demasiado similar a uno reciente → añadirlo a avoid_titles y reintentar
  3. Si el título es único → salir del bucle
```

Cada intento llama a `generate_article_with_ai`, que:

1. Construye el prompt con `build_generation_prompt`.
2. Intenta la **API Responses moderna** (`client.responses.create`).
3. Si falla, usa **Chat Completions** como fallback.
4. Extrae el bloque JSON de la respuesta con `_extract_json_block`.
5. Parsea el JSON con `_safe_json_loads` (tolerante a comillas tipográficas).
6. Devuelve `(title, summary, body)`.

---

### Paso 8 — Inserción en MongoDB

Si el título es único:

```python
doc = {
    "title": title, "slug": slug, "summary": summary, "body": body,
    "category": ObjectId(...), "tags": [tag_id],
    "author": author_id, "status": "published",
    "publishDate": now, "createdAt": now, ...
}
db[ARTICLES_COLL].insert_one(doc)
```

El **slug** se genera con `slugify(title)` y se garantiza que sea único con `next_available_slug` (añade `-2`, `-3`, etc. si ya existe).

---

### Paso 9 — Notificación y fin

- Si se publicó: email de éxito con título, slug y tag.
- Si no se publicó (todos los intentos fallaron): email de aviso.
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

### `next_available_slug(db, base_slug) → str`

Comprueba en MongoDB si el slug ya existe. Si es así, prueba `{base_slug}-2`, `{base_slug}-3`, etc., hasta encontrar uno libre.

---

## 7. Gestión de categorías, subcategorías y tags

La estructura de datos en MongoDB es jerárquica:

```
Categoría (ej. "Spring Boot")
  └── Subcategoría (ej. "Lombok")
        └── Tag (ej. "@Data")
```

Las relaciones entre documentos se resuelven mediante:

- El campo `parent` en una categoría apunta al `_id` de la categoría padre.
- Los tags pueden asociarse a una categoría/subcategoría mediante campos como `tags`, `tagIds`, `categoryId`, `categoryName`, `categories`, etc.

`build_hierarchy(categories)` construye dos índices:

- `by_id`: mapa `{str(_id) → documento}` para búsquedas O(1).
- `by_parent`: mapa `{str(parent_id) → [hijos]}` para recorrer el árbol.

`get_related_tags_for_category(cat, ...)` resuelve los tags de una categoría probando múltiples campos y estrategias de fallback, haciéndolo robusto ante esquemas distintos.

---

## 8. Integración con OpenAI

### Prompt generado

`build_generation_prompt(parent_name, subcat_name, tag_text, avoid_titles)` produce un prompt en español que instruye al modelo a devolver **únicamente un JSON** con la estructura:

```json
{
  "title": "...",
  "summary": "...",
  "body": "..."
}
```

El cuerpo (`body`) debe ser **HTML semántico** con `<h1>`, secciones `<h2>`, código en `<pre><code>`, FAQ y conclusión.

### Estrategia de llamada con fallback

El script intenta dos rutas distintas al SDK de OpenAI, en este orden:

```
1. client.responses.create(model, input=prompt)
   └── API Responses (disponible en openai-python ≥ 1.66.0, ~2025)
       Si el atributo no existe o la llamada falla →
2. client.chat.completions.create(model, messages)
   └── Chat Completions — endpoint estándar, siempre disponible
```

Este diseño garantiza compatibilidad hacia atrás: si la versión instalada del SDK no dispone del endpoint `responses`, la excepción se captura silenciosamente y el proceso continúa con Chat Completions. Ambas rutas tienen reintentos con **back-off exponencial** para errores transitorios (`ConnectionError`, `TimeoutError`).

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
    # Convierte a UTC para la consulta a MongoDB
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
```

Esto garantiza que el límite semanal **siempre se calcula en hora de Madrid** (incluyendo el cambio de horario de verano/invierno), independientemente del huso horario del servidor donde corra el script.

La variable `LIMIT_PUBLICATION=false` desactiva completamente esta comprobación, útil para entornos de prueba.

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

## 11. Documento insertado en MongoDB

El artículo que se inserta en la colección de artículos tiene la siguiente estructura:

```json
{
  "title":       "Cómo usar @Data en Lombok",
  "slug":        "como-usar-data-en-lombok",
  "summary":     "Resumen del artículo...",
  "body":        "<h1>...</h1><p>...</p>...",
  "category":    ObjectId("..."),
  "tags":        [ObjectId("...")],
  "author":      ObjectId("..."),
  "status":      "published",
  "likes":       [],
  "favoritedBy": [],
  "isVisible":   true,
  "publishDate": ISODate("..."),
  "generatedAt": ISODate("..."),
  "createdAt":   ISODate("..."),
  "updatedAt":   ISODate("..."),
  "images":      null
}
```

- `category` apunta a la **subcategoría** elegida (o a la categoría si no hay subcategoría).
- `tags` puede ser una lista vacía si no se encontró un tag disponible.
- Todas las fechas se almacenan en **UTC**.

---

## 12. Diagrama de flujo

```
┌─────────────────────────────────────────┐
│             INICIO (main)               │
└────────────────┬────────────────────────┘
                 │
        ┌────────▼────────┐
        │ ¿Variables OK?  │──── NO ──► Email error + sys.exit(1)
        └────────┬────────┘
                 │ SÍ
        ┌────────▼────────┐
        │ Conectar MongoDB│──── FALLA ──► Email error + sys.exit(1)
        └────────┬────────┘
                 │ OK
        ┌────────▼──────────────┐
        │ LIMIT_PUBLICATION=true│
        │ ¿Ya hay artículo      │
        │  esta semana?         │──── SÍ ──► Email aviso + sys.exit(0)
        └────────┬──────────────┘
                 │ NO
        ┌────────▼─────────────────┐
        │ Cargar categorías + tags  │
        │ Buscar usuario autor      │──── FALLA ──► Email error + sys.exit(1)
        └────────┬─────────────────┘
                 │ OK
        ┌────────▼──────────────────────┐
        │ Precargar IDs ya cubiertos     │
        │ (tags, categorías publicadas)  │
        └────────┬──────────────────────┘
                 │
        ┌────────▼─────────────────────────────────┐
        │ pick_fresh_target_strict()                │
        │ ¿Hay (parent, subcat, tag) disponible?   │──── NO ──► Email aviso + sys.exit(0)
        └────────┬─────────────────────────────────┘
                 │ SÍ
        ┌────────▼──────────────────────────────────────┐
        │ ensure_article_for_tag()                       │
        │  ┌──────────────────────────────────────────┐ │
        │  │  Bucle (máx. 5 intentos)                 │ │
        │  │   1. generate_article_with_ai()          │ │
        │  │   2. ¿Título demasiado similar?          │ │
        │  │      SÍ → añadir a avoid_titles, repetir│ │
        │  │      NO → aceptar título                 │ │
        │  └──────────────────────────────────────────┘ │
        │  ¿Título obtenido?                             │
        └────────┬───────────────────┬──────────────────┘
                 │ SÍ                │ NO
        ┌────────▼──────┐   ┌────────▼──────────────────┐
        │ INSERT artículo│   │ Email error (sin título)   │
        │ Email éxito    │   └───────────────────────────┘
        └────────┬───────┘
                 │
        ┌────────▼──────────────────┐
        │ FIN — Email "Proceso OK"  │
        └───────────────────────────┘
```
