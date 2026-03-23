"""
Módulo principal de generación de artículos con IA.

Este fichero actúa como punto de entrada CLI y como fachada pública que
re-exporta todos los símbolos de los submódulos para mantener la
compatibilidad con el código y los tests existentes.

Submódulos:
  config           – Constantes y configuración del entorno.
  utils            – Funciones auxiliares genéricas.
  html_utils       – Utilidades de procesamiento HTML.
  seo              – Funciones SEO (canonical URL, JSON-LD).
  notifications    – Sistema de notificaciones y email.
  prompts          – Construcción de prompts para la IA.
  ai_providers     – Proveedores de IA (LangChain, Ollama, Gemini).
  article_generator – Generación y guardado de artículos.
"""
from __future__ import annotations

import argparse
import smtplib  # noqa: F401 – re-exportado para compatibilidad con tests
import sys

from openai import OpenAI

# ── Re-exportar todos los símbolos públicos de los submódulos ──────────
from config import (  # noqa: F401
    AI_PROVIDER,
    ARTICLE_LANGUAGE,
    AI_TEMPERATURE_ARTICLE,
    AI_TEMPERATURE_TITLE,
    AUTHOR_USERNAME,
    FROM_EMAIL,
    GEMINI_API_KEY,
    GENERATION_SYSTEM_MSG,
    MAX_AVOID_TITLES_IN_PROMPT,
    MAX_TITLE_RETRIES,
    META_DESCRIPTION_MAX_LENGTH,
    META_TITLE_MAX_LENGTH,
    NOTIFY_VERBOSE,
    OLLAMA_BASE_URL,
    OLLAMA_PLACEHOLDER_API_KEY,
    OPENAIAPIKEY,
    OPENAI_MAX_ARTICLE_TOKENS,
    OPENAI_MAX_RETRIES,
    OPENAI_MAX_TITLE_TOKENS,
    OPENAI_MODEL,
    OPENAI_RETRY_BASE_DELAY,
    OUTPUT_FILENAME,
    OUTPUT_FILENAME_PATTERN,
    SEND_EMAILS,
    SEND_PROMPT_EMAIL,
    SIMILARITY_THRESHOLD_DEFAULT,
    SIMILARITY_THRESHOLD_STRICT,
    SITE,
    SMTP_HOST,
    SMTP_PASS,
    SMTP_PORT,
    SMTP_USER,
    TITLE_SYSTEM_MSG,
    TO_EMAIL,
    _LANGUAGE_NAMES,
    _language_name,
    logger,
)
from utils import (  # noqa: F401
    as_list,
    html_escape,
    is_too_similar,
    normalize_for_similarity,
    now_utc,
    similar_ratio,
    slugify,
    str_id,
    tag_name,
)
from html_utils import (  # noqa: F401
    _replace_h1,
    count_words,
    estimate_reading_time,
    extract_plain_text,
)
from seo import (  # noqa: F401
    build_canonical_url,
    build_json_ld_structured_data,
)
from notifications import (  # noqa: F401
    notify,
    send_notification_email,
)
from prompts import (  # noqa: F401
    build_generation_prompt,
    build_title_prompt,
    email_generation_prompt,
)
from ai_providers import (  # noqa: F401
    ChatGoogleGenerativeAI,
    ChatOpenAI,
    ChatPromptTemplate,
    LLMChain,
    StrOutputParser,
    _extract_json_block,
    _generate_with_langchain,
    _is_gemini_model,
    _is_ollama_provider,
    _retry_with_backoff,
    _safe_json_loads,
)
from article_generator import (  # noqa: F401
    generate_and_save_article,
    generate_article_with_ai,
    generate_title_with_ai,
)


# ============ MAIN ============
def main():
    parser = argparse.ArgumentParser(
        description="Genera un artículo técnico con IA y lo exporta a un fichero JSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--tag", "-t", default=None,
                        help="Tema o tag del artículo (opcional)")
    parser.add_argument("--category", "-c", required=True,
                        help="Nombre de la categoría padre (requerido)")
    parser.add_argument("--subcategory", "-s", default="General",
                        help="Nombre de la subcategoría")
    parser.add_argument("--output", "-o", default=OUTPUT_FILENAME,
                        help="Ruta del fichero JSON de salida (también configurable con OUTPUT_FILENAME en .env)")
    parser.add_argument("--username", "--author", "-u", "-a",
                        dest="username",
                        default=AUTHOR_USERNAME,
                        help="Username/nombre del autor (también configurable con AUTHOR_USERNAME en .env)")
    parser.add_argument("--site", "-S",
                        default=SITE,
                        help="URL base del sitio para URLs canónicas (p. ej. https://myblog.com), también configurable con SITE en .env")
    parser.add_argument("--language", "-l", default=ARTICLE_LANGUAGE,
                        help="Código de idioma ISO 639-1 (p. ej. es, en, fr)")
    parser.add_argument("--title", "-T", default=None,
                        help="Título del artículo (si se omite, se genera con IA)")
    parser.add_argument("--provider", "-p",
                        choices=["auto", "openai", "gemini", "ollama"],
                        default=None,
                        help="Proveedor de IA a usar (auto detecta por modelo/URL). "
                             "También configurable con AI_PROVIDER en .env")
    parser.add_argument("--avoid-titles", default="",
                        help="Títulos a evitar, separados por ';'")
    args = parser.parse_args()

    # Aplicar el proveedor de IA seleccionado por CLI (sobreescribe AI_PROVIDER del .env)
    if args.provider is not None:
        import config as _cfg
        _cfg.AI_PROVIDER = args.provider

    avoid_titles = [t.strip() for t in args.avoid_titles.split(";") if t.strip()] if args.avoid_titles else []

    notify("Inicio de proceso", "Comenzando generación de artículo.", level="info", always_email=True)

    # Validar que la clave de API esté disponible
    using_gemini = _is_gemini_model(OPENAI_MODEL)
    using_ollama = _is_ollama_provider()
    if using_ollama:
        pass  # Ollama no requiere clave de API
    elif using_gemini:
        if not GEMINI_API_KEY:
            notify("Configuración incompleta", "Falta la variable de entorno GEMINI_API_KEY.", level="error", always_email=True)
            sys.exit(1)
    else:
        if not OPENAIAPIKEY:
            notify("Configuración incompleta", "Falta la variable de entorno OPENAIAPIKEY.", level="error", always_email=True)
            sys.exit(1)

    # Inicializar cliente de IA (OpenAI SDK — para modelos ChatGPT y Ollama como fallback)
    client_ai: OpenAI | None = None
    if using_ollama:
        try:
            client_ai = OpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_PLACEHOLDER_API_KEY)
            notify("Ollama listo", f"Modelo: {OPENAI_MODEL} — URL: {OLLAMA_BASE_URL}", level="info", always_email=True)
        except Exception as e:
            notify("Error inicializando Ollama", str(e), level="error", always_email=True)
            sys.exit(1)
    elif not using_gemini:
        try:
            client_ai = OpenAI(api_key=OPENAIAPIKEY)
            notify("OpenAI listo", f"Modelo: {OPENAI_MODEL}", level="info", always_email=True)
        except Exception as e:
            notify("Error inicializando OpenAI", str(e), level="error", always_email=True)
            sys.exit(1)
    else:
        notify("Gemini listo", f"Modelo: {OPENAI_MODEL}", level="info", always_email=True)

    try:
        created = generate_and_save_article(
            client_ai=client_ai,
            tag_text=args.tag,
            parent_name=args.category,
            subcat_name=args.subcategory,
            avoid_titles=avoid_titles,
            author_name=args.username,
            site=args.site,
            language=args.language,
            output_path=args.output,
            title=args.title,
        )
    except Exception as e:
        notify("Error generando artículo", str(e), level="error", always_email=True)
        sys.exit(1)

    if created:
        notify("Proceso terminado", f"Artículo guardado en '{args.output}'.", level="success", always_email=True)
        print(f"\n🟩 Proceso terminado. Artículo guardado en '{args.output}'.")
    else:
        notify("Proceso terminado", "No se pudo generar el artículo.", level="warning", always_email=True)
        print("\n🟩 Proceso terminado. No se pudo generar el artículo.")

if __name__ == "__main__":
    main()
