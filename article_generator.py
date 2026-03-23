"""
article_generator.py
--------------------
Módulo principal de generación y guardado de artículos técnicos SEO.

Responsabilidades:
- Generar artículos completos (título + resumen + cuerpo HTML + keywords)
  mediante llamadas a la IA con LangChain, con fallback al SDK de OpenAI.
- Regenerar únicamente el título de un artículo cuando el generado es
  demasiado similar a títulos existentes (Fase 2 de deduplicación).
- Ensamblar el documento JSON completo con todos los metadatos SEO
  y guardarlo en el sistema de ficheros.

Algoritmo de dos fases para la generación de artículos únicos:

    **Fase 1** — Generación completa (llamada costosa):
        Llama a la IA con el prompt completo y obtiene título, resumen,
        cuerpo HTML y keywords. Si el título no es demasiado similar a
        los títulos en la lista ``avoid_titles`` (umbral 0.86), se usa
        directamente y la Fase 2 no se ejecuta.

    **Fase 2** — Regeneración solo del título (llamadas baratas):
        Si el título de la Fase 1 es demasiado similar, reutiliza el
        cuerpo HTML generado y regenera únicamente el título (hasta
        ``MAX_TITLE_RETRIES = 5`` veces). Actualiza el ``<h1>`` del
        cuerpo con el nuevo título aceptado.

El documento JSON generado incluye más de 25 campos con metadatos SEO:
``title``, ``slug``, ``summary``, ``body``, ``category``, ``tags``,
``author``, ``status``, ``keywords``, ``metaTitle``, ``metaDescription``,
``canonicalUrl``, ``structuredData`` (JSON-LD Schema.org), ``ogTitle``,
``ogDescription``, ``ogType``, ``wordCount``, ``readingTime``, y campos
de auditoría como ``publishDate``, ``createdAt``, ``updatedAt``.
"""
from __future__ import annotations

import json
import logging

from openai import OpenAI

import config
from utils import slugify, is_too_similar, html_escape
from html_utils import _replace_h1, count_words, estimate_reading_time
from seo import build_canonical_url, build_json_ld_structured_data
from notifications import notify
from prompts import build_generation_prompt, build_title_prompt, email_generation_prompt
from ai_providers import (
    _generate_with_langchain,
    _retry_with_backoff,
    _extract_json_block,
    _safe_json_loads,
    _is_gemini_model,
)
from utils import now_utc

logger = config.logger

_GEMINI_RECOMMENDED_MODELS = (
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
)
_GEMINI_RECOMMENDED_MODELS_STR = ", ".join(_GEMINI_RECOMMENDED_MODELS)


def _format_gemini_langchain_error(prefix: str, err: Exception) -> str:
    """Devuelve un mensaje de error accionable para fallos de LangChain con Gemini.

    Args:
        prefix: Prefijo base del mensaje de error.
        err: Excepción capturada al invocar LangChain.

    Returns:
        Mensaje de error formateado con guía accionable para el usuario.
    """
    raw_msg = str(err)
    lower_msg = raw_msg.lower()
    if (
        "api_key_invalid" in lower_msg
        or "api key not valid" in lower_msg
        or "invalid api key" in lower_msg
    ):
        return (
            f"{prefix}: GEMINI_API_KEY no es válida. "
            f"Este proyecto usa LangChain para Gemini. "
            f"Modelos recomendados: {_GEMINI_RECOMMENDED_MODELS_STR}. "
            f"Error original: {raw_msg}"
        )
    return f"{prefix}: {raw_msg}"


def generate_article_with_ai(client_ai: OpenAI | None, parent_name: str, subcat_name: str, tag_text: str, title: str | None = None, avoid_titles: list[str] | None = None, language: str = config.ARTICLE_LANGUAGE) -> tuple[str, str, str, list[str]]:
    """Genera un artículo técnico completo usando la IA configurada.

    Flujo de ejecución:
    1. Construye el prompt con :func:`~prompts.build_generation_prompt`.
    2. Llama a :func:`~ai_providers._generate_with_langchain` con reintentos
       via :func:`~ai_providers._retry_with_backoff`.
    3. Si LangChain falla (p. ej. proveedor no disponible), usa el SDK de OpenAI
       directamente como fallback (solo para modelos OpenAI/Ollama).
    4. Extrae el bloque JSON de la respuesta con :func:`~ai_providers._extract_json_block`.
    5. Parsea el JSON con :func:`~ai_providers._safe_json_loads`.
    6. Si el cuerpo HTML no tiene ``<h1>``, lo antepone con el título escapado.

    Args:
        client_ai:     Cliente :class:`~openai.OpenAI` para el fallback SDK.
                       Puede ser ``None`` cuando se usa Gemini (sin fallback SDK).
        parent_name:   Nombre de la categoría padre (p. ej. ``"Spring Boot"``).
        subcat_name:   Nombre de la subcategoría (p. ej. ``"Spring Security"``).
        tag_text:      Tema o tag del artículo (p. ej. ``"JWT Authentication"``).
        title:         Si se proporciona, la IA genera el contenido alrededor de
                       este título en lugar de generar uno nuevo.
        avoid_titles:  Lista de títulos a evitar en el prompt.
        language:      Código ISO 639-1 del idioma (por defecto ``config.ARTICLE_LANGUAGE``).

    Returns:
        Tupla ``(title, summary, body_html, keywords)`` donde:
        - ``title``: título del artículo.
        - ``summary``: meta-descripción SEO (≤ 160 caracteres idealmente).
        - ``body_html``: cuerpo HTML semántico completo.
        - ``keywords``: lista de palabras clave SEO.

    Raises:
        :class:`RuntimeError`: Si la IA no devuelve contenido tras todos los reintentos.
        :class:`ValueError`: Si la respuesta JSON no contiene ``title`` o ``body``.
    """
    user_prompt = build_generation_prompt(parent_name, subcat_name, tag_text, title=title, avoid_titles=avoid_titles, language=language)

    raw_text = None

    # 1) Intento con LangChain — con reintentos
    def _call_langchain_article():
        return _generate_with_langchain(
            config.GENERATION_SYSTEM_MSG,
            user_prompt,
            max_tokens=config.OPENAI_MAX_ARTICLE_TOKENS,
            temperature=config.AI_TEMPERATURE_ARTICLE,
        )

    try:
        raw_text = _retry_with_backoff(_call_langchain_article)
    except Exception as e:
        if _is_gemini_model(config.OPENAI_MODEL):
            raise RuntimeError(_format_gemini_langchain_error("Fallo en LangChain con Gemini", e)) from e
        logger.info("LangChain no disponible para artículo; usando SDK como fallback.")
        raw_text = None

    # 2) Fallback: OpenAI SDK Chat Completions — solo para modelos OpenAI/ChatGPT
    if not raw_text and not _is_gemini_model(config.OPENAI_MODEL) and client_ai is not None:
        def _call_chat():
            chat = client_ai.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": config.GENERATION_SYSTEM_MSG},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=config.AI_TEMPERATURE_ARTICLE,
                max_tokens=config.OPENAI_MAX_ARTICLE_TOKENS,
            )
            return chat.choices[0].message.content

        try:
            raw_text = _retry_with_backoff(_call_chat)
        except Exception as e:
            raise RuntimeError(f"Fallo llamando a OpenAI: {e}")

    if not raw_text:
        raise RuntimeError("El modelo no devolvió contenido.")

    json_text = _extract_json_block(raw_text)
    data = _safe_json_loads(json_text)

    title = str(data.get("title", "")).strip()
    summary = str(data.get("summary", "")).strip()
    body = str(data.get("body", "")).strip()

    if not title or not body:
        raise ValueError("La respuesta del modelo no contiene 'title' y/o 'body'.")

    # Asegura <h1> acorde al título si falta
    if "<h1" not in body.lower():
        safe_title = html_escape(title)
        body = f'<h1>{safe_title}</h1>\n' + body

    raw_keywords = data.get("keywords", [])
    keywords: list[str] = (
        [str(k).strip() for k in raw_keywords if str(k).strip()]
        if isinstance(raw_keywords, list) else []
    )

    return title, summary, body, keywords

def generate_title_with_ai(client_ai: OpenAI | None, parent_name: str, subcat_name: str, tag_text: str, avoid_titles: list[str] | None = None, language: str = config.ARTICLE_LANGUAGE) -> str:
    """Genera únicamente el título de un artículo usando la IA configurada.

    Mucho más económico que :func:`generate_article_with_ai` porque solo
    pide el título sin cuerpo ni keywords. Se usa en la Fase 2 del algoritmo
    de deduplicación cuando el título generado en la Fase 1 es demasiado
    similar a uno existente.

    Flujo de ejecución:
    1. Construye el prompt ligero con :func:`~prompts.build_title_prompt`.
    2. Llama a :func:`~ai_providers._generate_with_langchain` con reintentos.
    3. Fallback al SDK de OpenAI si LangChain no está disponible.
    4. Limpia la respuesta (elimina comillas y espacios) y la trunca a
       ``META_TITLE_MAX_LENGTH`` caracteres.

    Args:
        client_ai:     Cliente :class:`~openai.OpenAI` para el fallback SDK.
        parent_name:   Nombre de la categoría padre.
        subcat_name:   Nombre de la subcategoría.
        tag_text:      Tema o tag del artículo.
        avoid_titles:  Lista de títulos a evitar.
        language:      Código ISO 639-1 del idioma (por defecto ``config.ARTICLE_LANGUAGE``).

    Returns:
        Título generado como cadena de texto, truncado a 60 caracteres.

    Raises:
        :class:`RuntimeError`: Si la IA no devuelve contenido tras todos los reintentos.
    """
    user_prompt = build_title_prompt(parent_name, subcat_name, tag_text, avoid_titles=avoid_titles, language=language)
    raw_text = None

    # 1) Intento con LangChain — con reintentos
    def _call_langchain_title():
        return _generate_with_langchain(
            config.TITLE_SYSTEM_MSG,
            user_prompt,
            max_tokens=config.OPENAI_MAX_TITLE_TOKENS,
            temperature=config.AI_TEMPERATURE_TITLE,
        )

    try:
        raw_text = _retry_with_backoff(_call_langchain_title)
    except Exception as e:
        if _is_gemini_model(config.OPENAI_MODEL):
            raise RuntimeError(_format_gemini_langchain_error("Fallo en LangChain con Gemini para título", e)) from e
        logger.info("LangChain no disponible para título; usando SDK como fallback.")
        raw_text = None

    # 2) Fallback: OpenAI SDK Chat Completions — solo para modelos OpenAI/ChatGPT
    if not raw_text and not _is_gemini_model(config.OPENAI_MODEL) and client_ai is not None:
        def _call_chat():
            chat = client_ai.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": config.TITLE_SYSTEM_MSG},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=config.AI_TEMPERATURE_TITLE,
                max_tokens=config.OPENAI_MAX_TITLE_TOKENS,
            )
            return chat.choices[0].message.content

        try:
            raw_text = _retry_with_backoff(_call_chat)
        except Exception as e:
            raise RuntimeError(f"Fallo generando título con OpenAI: {e}")

    if not raw_text:
        raise RuntimeError("El modelo no devolvió contenido para el título.")

    return raw_text.strip().strip("\"'").strip()[:config.META_TITLE_MAX_LENGTH]

def generate_and_save_article(
    client_ai: OpenAI | None,
    tag_text: str | None,
    parent_name: str,
    subcat_name: str,
    avoid_titles: list[str] | None = None,
    author_name: str = config.AUTHOR_USERNAME,
    site: str = config.SITE,
    language: str = config.ARTICLE_LANGUAGE,
    output_path: str = "article.json",
    title: str | None = None,
) -> bool:
    """Genera un artículo técnico SEO con IA y lo guarda en un fichero JSON.

    Orquesta el flujo completo de generación:

    1. **Envío del prompt por email** (opcional): si ``SEND_PROMPT_EMAIL=true``,
       envía el prompt a la dirección configurada antes de llamar a la IA.

    2. **Título explícito** (si *title* no es ``None``): llama a
       :func:`generate_article_with_ai` pasando el título como contexto y
       reemplaza el ``<h1>`` del cuerpo con :func:`~html_utils._replace_h1`.

    3. **Generación automática con deduplicación** (si *title* es ``None``):

       - **Fase 1**: Genera el artículo completo. Si el título no es similar
         a ningún elemento de *avoid_titles* (umbral 0.86), lo acepta.
       - **Fase 2**: Si el título es demasiado similar, reutiliza el cuerpo
         y regenera solo el título (hasta ``MAX_TITLE_RETRIES = 5`` veces)
         con :func:`generate_title_with_ai`.

    4. **Generación de metadatos SEO**: slug, word_count, reading_time,
       meta_title, meta_description, canonical_url, JSON-LD, Open Graph.

    5. **Guardado a JSON**: serializa el documento completo en *output_path*
       con ``ensure_ascii=False`` e indentación de 2 espacios.

    6. **Notificación de éxito**: envía email y muestra mensaje en consola.

    Args:
        client_ai:     Cliente :class:`~openai.OpenAI` (puede ser ``None`` con Gemini).
        tag_text:      Tema o tag del artículo. Si es ``None``, se usa solo la categoría.
        parent_name:   Nombre de la categoría padre (requerido).
        subcat_name:   Nombre de la subcategoría.
        avoid_titles:  Lista de títulos existentes a evitar (deduplicación).
        author_name:   Nombre del autor del artículo.
        site:          URL base del sitio para URLs canónicas y JSON-LD.
        language:      Código ISO 639-1 del idioma.
        output_path:   Ruta del fichero JSON de salida.
        title:         Título explícito. Si se proporciona, se omite la Fase 1/2.

    Returns:
        ``True`` si el artículo se generó y guardó correctamente;
        ``False`` si no se pudo generar un título único tras todos los intentos.
    """
    avoid_titles = list(avoid_titles) if avoid_titles else []

    # Opcional: enviar el prompt por email antes de generar con OpenAI
    if config.SEND_PROMPT_EMAIL:
        try:
            email_generation_prompt(parent_name, subcat_name, tag_text, avoid_titles=avoid_titles)
            notify("Prompt enviado por email", "Se envió el prompt de generación a la dirección configurada.", level="info", always_email=False)
        except Exception as e:
            notify("Error enviando prompt por email", str(e), level="warning", always_email=True)

    # Si el título se proporcionó como argumento, generar el cuerpo con ese título como contexto
    if title:
        t, s, b, kw = generate_article_with_ai(client_ai, parent_name, subcat_name, tag_text, title=title, avoid_titles=avoid_titles, language=language)
        # Usar el título proporcionado (no el generado por la IA) y ajustar el <h1>
        title, summary, body, keywords = title, s, _replace_h1(b, title), kw
    else:
        max_attempts = config.MAX_TITLE_RETRIES
        title = summary = body = None
        keywords: list[str] = []

        # Fase 1: Generar el artículo completo (única llamada costosa a OpenAI)
        t, s, b, kw = generate_article_with_ai(client_ai, parent_name, subcat_name, tag_text, avoid_titles=avoid_titles, language=language)

        if not is_too_similar(t, avoid_titles, threshold=config.SIMILARITY_THRESHOLD_STRICT):
            title, summary, body, keywords = t, s, b, kw
        else:
            # Fase 2: El cuerpo del artículo es válido; sólo regenerar el título (llamadas ligeras)
            notify("Título similar detectado", f"Intento 1/{max_attempts}: '{t}'. Regenerando sólo el título...", level="warning", always_email=True)
            avoid_titles.append(t)
            for attempt in range(2, max_attempts + 1):
                new_t = generate_title_with_ai(client_ai, parent_name, subcat_name, tag_text, avoid_titles=avoid_titles, language=language)
                if not is_too_similar(new_t, avoid_titles, threshold=config.SIMILARITY_THRESHOLD_STRICT):
                    title, summary, body, keywords = new_t, s, _replace_h1(b, new_t), kw
                    break
                notify("Título similar detectado", f"Intento {attempt}/{max_attempts}: '{new_t}'. Reintentando...", level="warning", always_email=True)
                avoid_titles.append(new_t)

    if not title or not body:
        notify("No se pudo generar título único", "Tras varios intentos no se logró un título suficientemente diferente.", level="error", always_email=True)
        return False

    slug = slugify(title)
    now = now_utc()
    now_iso = now.isoformat()

    word_count = count_words(body)
    reading_time = estimate_reading_time(body)
    meta_title = title[:config.META_TITLE_MAX_LENGTH].rstrip() if len(title) > config.META_TITLE_MAX_LENGTH else title
    meta_description = summary[:config.META_DESCRIPTION_MAX_LENGTH].rstrip() if len(summary) > config.META_DESCRIPTION_MAX_LENGTH else summary
    canonical_url = build_canonical_url(site, slug)

    # Datos estructurados JSON-LD (Schema.org) para SEO
    structured_data = build_json_ld_structured_data(
        title=title,
        summary=summary,
        canonical_url=canonical_url,
        keywords=keywords,
        author_name=author_name,
        date_published=now_iso,
        date_modified=now_iso,
        word_count=word_count,
        reading_time=reading_time,
        category_name=subcat_name,
        tag_names=[tag_text] if tag_text else [],
        site=site,
        language=language,
    )

    doc = {
        "title": title,
        "slug": slug,
        "summary": summary,
        "body": body,
        "category": subcat_name,
        "tags": [tag_text] if tag_text else [],
        "author": author_name,
        "status": "published",
        "likes": [],
        "favoritedBy": [],
        "isVisible": True,
        "publishDate": now_iso,
        "generatedAt": now_iso,
        "createdAt": now_iso,
        "updatedAt": now_iso,
        "images": None,
        "wordCount": word_count,
        "readingTime": reading_time,
        "keywords": keywords,
        "metaTitle": meta_title,
        "metaDescription": meta_description,
        "canonicalUrl": canonical_url,
        "structuredData": structured_data,
        "ogTitle": meta_title,
        "ogDescription": meta_description,
        "ogType": "article",
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    notify("Artículo generado",
           f"Título: {title}<br>Slug: {site}/post/{slug if site else slug}<br>Tag: {tag_text or ''}",
           level="success", always_email=True)
    return True
