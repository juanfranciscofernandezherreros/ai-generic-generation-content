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


def generate_article_with_ai(client_ai: OpenAI | None, parent_name: str, subcat_name: str, tag_text: str, title: str | None = None, avoid_titles: list[str] | None = None, language: str = config.ARTICLE_LANGUAGE) -> tuple[str, str, str, list[str]]:
    """
    Genera el artículo usando LangChain (ChatOpenAI, ChatGoogleGenerativeAI o Ollama según el modelo).
    Para modelos OpenAI/ChatGPT y Ollama usa el SDK de OpenAI directamente como fallback si LangChain falla.
    Incluye reintentos con back-off exponencial para errores transitorios.
    Si se proporciona ``title``, el prompt instruye a la IA a generar el contenido alrededor de ese título.
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
    except Exception:
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
    """
    Genera únicamente el título del artículo usando LangChain (ChatOpenAI, ChatGoogleGenerativeAI o Ollama).
    Para modelos OpenAI/ChatGPT y Ollama usa el SDK de OpenAI directamente como fallback si LangChain falla.
    Mucho más económico que regenerar el artículo completo en cada reintento.
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
    except Exception:
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
    """Genera un artículo con IA y lo guarda en un fichero JSON."""
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
