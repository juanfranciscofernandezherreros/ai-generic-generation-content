import argparse
import difflib
import json
import logging
import math
import os
import random
import re
import smtplib
import sys
import time as _time
import unicodedata
from collections.abc import Callable
from datetime import datetime, timezone
from email.header import Header
from email.message import EmailMessage
from typing import Any, Union

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from openai import OpenAI

# ============ LOGGING ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger(__name__)

# ============ CARGA .env ============
# Busca el .env en la carpeta actual del script
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# ============ CONFIG DESDE ENTORNO ============
SITE            = os.getenv("SITE") or ""
OPENAIAPIKEY    = os.getenv("OPENAIAPIKEY")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")  # p. ej. http://localhost:11434/v1
AUTHOR_USERNAME = os.getenv("AUTHOR_USERNAME") or "adminUser"
OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "gpt-4o")

# Notificaciones
SMTP_HOST   = os.getenv("SMTP_HOST")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
FROM_EMAIL  = os.getenv("FROM_EMAIL") or (SMTP_USER or "")
TO_EMAIL    = os.getenv("NOTIFY_EMAIL") or "jnfz92@gmail.com"
NOTIFY_VERBOSE = (os.getenv("NOTIFY_VERBOSE", "true").lower() in ("1","true","yes","y"))
# Si es true, enviará por email el prompt de generación antes de llamar a OpenAI
SEND_PROMPT_EMAIL = (os.getenv("SEND_PROMPT_EMAIL", "false").lower() in ("1", "true", "yes", "y"))
# Idioma por defecto para los artículos generados (código ISO 639-1, p. ej. "es", "en", "fr")
ARTICLE_LANGUAGE = os.getenv("ARTICLE_LANGUAGE", "es")
# Temperature para la generación de artículos y títulos (0.0 – 1.0)
AI_TEMPERATURE_ARTICLE = float(os.getenv("AI_TEMPERATURE_ARTICLE", "0.7"))
AI_TEMPERATURE_TITLE   = float(os.getenv("AI_TEMPERATURE_TITLE",   "0.9"))

# ============ CONSTANTS ============
SIMILARITY_THRESHOLD_DEFAULT = 0.82   # umbral para is_too_similar genérico
SIMILARITY_THRESHOLD_STRICT  = 0.86   # umbral usado al reintentar títulos
MAX_TITLE_RETRIES            = 5      # intentos máx. para generar título único
OPENAI_MAX_RETRIES           = 3      # reintentos para llamadas a OpenAI
OPENAI_RETRY_BASE_DELAY      = 2      # seg. base para backoff exponencial
META_TITLE_MAX_LENGTH        = 60     # máx. caracteres para metaTitle SEO
META_DESCRIPTION_MAX_LENGTH  = 160    # máx. caracteres para metaDescription SEO
MAX_AVOID_TITLES_IN_PROMPT   = 5      # máx. títulos a incluir en el prompt (mantiene prompts cortos)
OPENAI_MAX_ARTICLE_TOKENS    = 4096   # límite de tokens de salida para artículos
OPENAI_MAX_TITLE_TOKENS      = 100    # límite de tokens de salida para títulos
OLLAMA_PLACEHOLDER_API_KEY   = "ollama"  # clave ficticia para Ollama (no requiere autenticación)

# ============ IDIOMAS ============
# Mapa de códigos ISO 639-1 a nombres de idioma (escritos en español, para usar en los prompts)
_LANGUAGE_NAMES: dict[str, str] = {
    "es": "español",
    "en": "inglés",
    "fr": "francés",
    "de": "alemán",
    "it": "italiano",
    "pt": "portugués",
    "nl": "neerlandés",
    "pl": "polaco",
    "ru": "ruso",
    "zh": "chino",
    "ja": "japonés",
    "ar": "árabe",
}

def _language_name(code: str) -> str:
    """Devuelve el nombre del idioma (en español) para un código ISO 639-1.
    Si el código no está en el mapa, devuelve el propio código."""
    return _LANGUAGE_NAMES.get(code.lower(), code)

# ============ SYSTEM MESSAGES (reutilizados en ambas APIs) ============
GENERATION_SYSTEM_MSG = (
    "Eres redactor técnico sénior y experto en SEO especializado en tecnología y desarrollo de software. "
    "Generas contenido optimizado para motores de búsqueda con HTML semántico, "
    "estructura de encabezados jerárquica (h1 > h2 > h3), uso estratégico de palabras clave "
    "y metadatos precisos. "
    "El contenido que redactas está siempre relacionado con la categoría y el tag indicados en el prompt. "
    "Devuelves SOLO JSON válido con: title, summary, body (HTML semántico), keywords."
)
TITLE_SYSTEM_MSG = (
    "Eres experto en SEO técnico. "
    "Devuelve solo el título solicitado, sin comillas ni texto adicional."
)

# ============ HELPERS ============
def str_id(x: Any) -> str:
    return str(x)

def as_list(v: Any) -> list:
    if v is None: return []
    if isinstance(v, (list, tuple, set)): return list(v)
    return [v]

def tag_name(t: dict[str, Any]) -> str:
    return str(t.get("name") or t.get("tag") or t.get("_id"))

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text

def normalize_for_similarity(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower()
    s = re.sub(r"[\W_]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def similar_ratio(a: str, b: str) -> float:
    a_norm, b_norm = normalize_for_similarity(a), normalize_for_similarity(b)
    if not a_norm or not b_norm: return 0.0
    return difflib.SequenceMatcher(None, a_norm, b_norm).ratio()

def is_too_similar(title: str, candidates: list, threshold: float = 0.82) -> bool:
    for c in candidates:
        if similar_ratio(title, c) >= threshold:
            return True
    return False

def now_utc():
    return datetime.now(tz=timezone.utc)

def html_escape(s: str) -> str:
    """Escapa &, <, > para HTML simple en correos."""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )

def _replace_h1(body: str, title: str) -> str:
    """Reemplaza el primer <h1> del cuerpo con el título dado, o lo antepone si no existe."""
    escaped_title = html_escape(title)
    new_body, replacements = re.subn(
        r'<h1[^>]*>.*?</h1>', f'<h1>{escaped_title}</h1>',
        body, count=1, flags=re.DOTALL | re.IGNORECASE,
    )
    if not replacements:
        new_body = f'<h1>{escaped_title}</h1>\n' + body
    return new_body

def extract_plain_text(html: str) -> str:
    """Elimina todas las etiquetas HTML y devuelve el texto plano sin espacios múltiples."""
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()

def count_words(html: str) -> int:
    """Cuenta las palabras de un cuerpo HTML."""
    text = extract_plain_text(html)
    return len(text.split()) if text else 0

def estimate_reading_time(body_html: str, wpm: int = 230) -> int:
    """Devuelve el tiempo de lectura estimado en minutos (mínimo 1, redondeando hacia arriba)."""
    words = count_words(body_html)
    return max(1, math.ceil(words / wpm))

def build_canonical_url(site: str, slug: str) -> str:
    """Construye la URL canónica del artículo a partir del dominio y el slug."""
    if not site or not slug:
        return ""
    base = site.rstrip("/")
    return f"{base}/post/{slug}"

def build_json_ld_structured_data(
    title: str,
    summary: str,
    canonical_url: str,
    keywords: list[str],
    author_name: str,
    date_published: str,
    date_modified: str,
    word_count: int,
    reading_time: int,
    category_name: str,
    tag_names: list[str],
    site: str,
    language: str = ARTICLE_LANGUAGE,
) -> dict:
    """
    Genera datos estructurados JSON-LD (Schema.org) de tipo Article.

    Estos datos permiten a los motores de búsqueda (Google, Bing, etc.)
    entender mejor el contenido del artículo, mejorando la visibilidad
    en resultados enriquecidos (rich snippets).
    """
    base_url = site.rstrip("/") if site else ""
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": title[:110],
        "description": summary[:200],
        "author": {
            "@type": "Person",
            "name": author_name,
        },
        "datePublished": date_published,
        "dateModified": date_modified,
        "wordCount": word_count,
        "timeRequired": f"PT{reading_time}M",
        "inLanguage": language,
        "keywords": ", ".join(keywords) if keywords else "",
        "articleSection": category_name,
    }
    if canonical_url:
        data["url"] = canonical_url
        data["mainEntityOfPage"] = {"@type": "WebPage", "@id": canonical_url}
    if base_url:
        data["publisher"] = {
            "@type": "Organization",
            "name": base_url.replace("https://", "").replace("http://", ""),
            "url": base_url,
        }
    if tag_names:
        data["about"] = [{"@type": "Thing", "name": t} for t in tag_names]
    return data

# ========= Notificaciones / logging =========
def send_notification_email(subject: str, html_body: str, text_body: str = None):
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, FROM_EMAIL, TO_EMAIL]):
        print("⚠️  Faltan variables SMTP para enviar el correo. Se omite el envío.")
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = str(Header(subject, "utf-8"))
        msg["From"] = FROM_EMAIL
        msg["To"] = TO_EMAIL
        text_body = text_body or "Notificación del proceso."
        msg.set_content(text_body, charset="utf-8")
        msg.add_alternative(html_body, subtype="html", charset="utf-8")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT,
                          local_hostname="localhost") as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        print(f"📧 Notificación enviada a {TO_EMAIL}: {subject}")
        return True
    except Exception as e:
        print(f"❌ Error enviando el correo: {e}", file=sys.stderr)
        return False

def notify(subject: str, message: str, level: str = "info", always_email: bool = True):
    """
    Centraliza impresión y envío de email. Si NOTIFY_VERBOSE es False,
    sólo envía emails para level in ['error','warning'] salvo que always_email=True.
    """
    stamp = now_utc().isoformat()
    prefix = {"info":"ℹ️","success":"✅","warning":"⚠️","error":"❌"}.get(level, "ℹ️")
    line = f"{prefix} [{stamp}] {subject} :: {message}"
    print(line)
    should_email = always_email or NOTIFY_VERBOSE or (level in ("error","warning"))
    if should_email:
        html = f"<p><b>{subject}</b></p><p>{message}</p><p><small>{stamp} UTC</small></p>"
        send_notification_email(subject=f"[{level.upper()}] {subject}", html_body=html, text_body=f"{subject}\n\n{message}\n\n{stamp} UTC")

# ========= Retry con back-off exponencial =========
def _retry_with_backoff(fn: Callable, max_retries: int = OPENAI_MAX_RETRIES, base_delay: float = OPENAI_RETRY_BASE_DELAY) -> Any:
    """Ejecuta *fn()* con reintentos y back-off exponencial. Reintenta solo errores transitorios."""
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn()
        except (ConnectionError, TimeoutError) as exc:
            last_exc = exc
            wait = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            logger.warning("Reintento %d/%d tras error transitorio: %s (espera %.1fs)", attempt, max_retries, exc, wait)
            _time.sleep(wait)
        except Exception:
            raise
    raise RuntimeError(f"Falló tras {max_retries} reintentos") from last_exc

def build_generation_prompt(parent_name: str, subcat_name: str, tag_text: str | None = None, avoid_titles: list[str] | None = None, language: str = ARTICLE_LANGUAGE) -> str:
    avoid_titles = avoid_titles or []
    avoid_block = ""
    if avoid_titles:
        avoid_list = [t.replace('"', '\"') for t in avoid_titles[:MAX_AVOID_TITLES_IN_PROMPT]]
        avoid_block = (
            "\nEvita títulos iguales o muy similares a: "
            + "; ".join(f'"{t}"' for t in avoid_list)
        )
    lang = _language_name(language)
    topic = f'sobre "{tag_text}" ' if tag_text else ""
    return f"""Artículo SEO en {lang} {topic}(categoría: "{parent_name}", subcategoría: "{subcat_name}").
Devuelve SOLO JSON: {{"title":"...","summary":"...","body":"...","keywords":[...]}}

title: optimizado para SEO y CTR, conciso (máx. 60 caracteres), incluye palabra clave principal al inicio.
summary: meta-descripción SEO (máx. 160 caracteres), incluye palabra clave, llamada a la acción implícita.
keywords: 5-7 palabras clave SEO en minúsculas (long-tail incluidas), sin repetir el título exacto.
body (HTML semántico bien cerrado, optimizado para SEO on-page):
- <h1> con título (sin emojis), palabra clave principal incluida.
- Intro <p> que enganche, presente el problema y contenga la keyword principal.
- 3-5 secciones <h2> con keywords secundarias: explicación técnica, buenas prácticas, casos reales.
- Subsecciones <h3> donde sea necesario para profundizar.
- Código en <pre><code class="language-...">. Funcional, copiable, con comentarios descriptivos.
- Usa <strong> y <em> para resaltar términos clave (sin abusar).
- <h2> FAQ (Preguntas frecuentes): 3-5 preguntas en <h3> con respuestas en <p>. Redacta preguntas como búsquedas reales de usuarios.
- <h2> Conclusión con resumen de puntos clave y CTA (llamada a la acción).
- Listas <ul>/<ol> para ventajas, pasos o comparativas.
- Párrafos cortos (3-4 líneas máx.) para mejorar la legibilidad.

Tono profesional, sin relleno. JSON con comillas escapadas.{avoid_block}
"""

def build_title_prompt(parent_name: str, subcat_name: str, tag_text: str | None = None, avoid_titles: list[str] | None = None, language: str = ARTICLE_LANGUAGE) -> str:
    """Construye un prompt ligero para generar únicamente el título de un artículo."""
    avoid_titles = avoid_titles or []
    avoid_block = ""
    if avoid_titles:
        avoid_list = [t.replace('"', '\\"') for t in avoid_titles[:MAX_AVOID_TITLES_IN_PROMPT]]
        avoid_block = (
            "\nEvita títulos iguales o muy similares a cualquiera de estos: "
            + "; ".join(f'"{t}"' for t in avoid_list)
        )
    lang = _language_name(language)
    topic = f'para el tema "{tag_text}" ' if tag_text else ""
    return (
        f'Genera un título de artículo técnico en {lang} {topic}'
        f'(categoría: "{parent_name}", subcategoría: "{subcat_name}").\n'
        f"Requisitos: atractivo, conciso (máx. {META_TITLE_MAX_LENGTH} caracteres), "
        f"optimizado para SEO, incluye la palabra clave principal.{avoid_block}\n"
        "Devuelve ÚNICAMENTE el texto del título, sin comillas ni texto adicional."
    )

def email_generation_prompt(parent_name: str, subcat_name: str, tag_text: str | None = None, avoid_titles=None):
    """
    Construye el prompt y lo envía por email usando SMTP ya configurado.
    NO intenta parsear ninguna respuesta de OpenAI (solo notifica).
    Devuelve el prompt por si quieres loguearlo.
    """
    prompt = build_generation_prompt(parent_name, subcat_name, tag_text, avoid_titles=avoid_titles)
    html = f"<h3>Prompt de generación</h3><p>Se envía el prompt que se usará con OpenAI:</p><pre style=\"white-space:pre-wrap; word-break:break-word;\">{html_escape(prompt)}</pre>"
    send_notification_email(subject="Prompt de generación", html_body=html, text_body=prompt)
    return prompt

# ====== Utilidades de parseo/IA ======
def _extract_json_block(text: str) -> str:
    """
    Extrae el primer bloque que parezca JSON del texto (soporta ```json ... ``` o texto suelto).
    """
    if not text:
        return ""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    brace = re.search(r"\{.*\}", text, flags=re.DOTALL)
    return brace.group(0).strip() if brace else text.strip()

def _safe_json_loads(s: str) -> dict:
    try:
        return json.loads(s)
    except Exception:
        s2 = s.replace("\u201c", "\"").replace("\u201d", "\"").replace("\u2019", "'")
        return json.loads(s2)

def _is_gemini_model(model: str) -> bool:
    """Devuelve True si el nombre de modelo corresponde a un modelo de Google Gemini."""
    return model.lower().startswith("gemini")


def _is_ollama_provider() -> bool:
    """Devuelve True si se ha configurado OLLAMA_BASE_URL para usar un servidor Ollama local."""
    return bool(OLLAMA_BASE_URL)


class LLMChain:
    """
    Cadena que combina un ChatPromptTemplate con un modelo de lenguaje (LLM).
    Implementa el patrón LLMChain usando LCEL (LangChain Expression Language):
      prompt | llm | StrOutputParser()
    Uso:
        chain = LLMChain(llm=llm, prompt=prompt_template)
        result = chain.run(user_prompt="Escribe un artículo sobre Python")
    """

    def __init__(self, llm: Union["ChatOpenAI", "ChatGoogleGenerativeAI"], prompt: ChatPromptTemplate) -> None:
        self._chain = prompt | llm | StrOutputParser()

    def run(self, **input_variables) -> str:
        """Ejecuta la cadena con las variables del prompt y devuelve el texto generado."""
        return self._chain.invoke(input_variables)

    def invoke(self, input_dict: dict[str, Any]) -> str:
        """Ejecuta la cadena con un diccionario de variables del prompt y devuelve el texto generado.

        Args:
            input_dict: Diccionario con las variables definidas en el ChatPromptTemplate,
                        por ejemplo ``{"user_prompt": "Escribe un artículo sobre Python"}``.
        """
        return self._chain.invoke(input_dict)


def _generate_with_langchain(
    system_msg: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float = 0.7,
) -> str:
    """
    Invoca el modelo de lenguaje mediante LangChain usando LLMChain.
    Usa ChatGoogleGenerativeAI para modelos Gemini, ChatOpenAI con base_url
    para Ollama (servidor local) y ChatOpenAI estándar para modelos OpenAI/ChatGPT.
    Devuelve el texto generado como string.
    Lanza RuntimeError si la llamada falla o no devuelve contenido.
    """
    if _is_gemini_model(OPENAI_MODEL):
        llm = ChatGoogleGenerativeAI(
            model=OPENAI_MODEL,
            google_api_key=GEMINI_API_KEY,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
    elif _is_ollama_provider():
        llm = ChatOpenAI(
            model=OPENAI_MODEL,
            base_url=OLLAMA_BASE_URL,
            api_key=OLLAMA_PLACEHOLDER_API_KEY,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    else:
        llm = ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAIAPIKEY,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_msg),
        ("human", "{user_prompt}"),
    ])
    chain = LLMChain(llm=llm, prompt=prompt_template)
    result = chain.run(user_prompt=user_prompt)
    if not result:
        raise RuntimeError("LangChain no devolvió contenido.")
    return result

def generate_article_with_ai(client_ai: OpenAI | None, parent_name: str, subcat_name: str, tag_text: str, avoid_titles: list[str] | None = None, language: str = ARTICLE_LANGUAGE) -> tuple[str, str, str, list[str]]:
    """
    Genera el artículo usando LangChain (ChatOpenAI, ChatGoogleGenerativeAI o Ollama según el modelo).
    Para modelos OpenAI/ChatGPT y Ollama usa el SDK de OpenAI directamente como fallback si LangChain falla.
    Incluye reintentos con back-off exponencial para errores transitorios.
    """
    user_prompt = build_generation_prompt(parent_name, subcat_name, tag_text, avoid_titles=avoid_titles, language=language)

    raw_text = None

    # 1) Intento con LangChain — con reintentos
    def _call_langchain_article():
        return _generate_with_langchain(
            GENERATION_SYSTEM_MSG,
            user_prompt,
            max_tokens=OPENAI_MAX_ARTICLE_TOKENS,
            temperature=AI_TEMPERATURE_ARTICLE,
        )

    try:
        raw_text = _retry_with_backoff(_call_langchain_article)
    except Exception:
        logger.info("LangChain no disponible para artículo; usando SDK como fallback.")
        raw_text = None

    # 2) Fallback: OpenAI SDK Chat Completions — solo para modelos OpenAI/ChatGPT
    if not raw_text and not _is_gemini_model(OPENAI_MODEL) and client_ai is not None:
        def _call_chat():
            chat = client_ai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": GENERATION_SYSTEM_MSG},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=AI_TEMPERATURE_ARTICLE,
                max_tokens=OPENAI_MAX_ARTICLE_TOKENS,
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

def generate_title_with_ai(client_ai: OpenAI | None, parent_name: str, subcat_name: str, tag_text: str, avoid_titles: list[str] | None = None, language: str = ARTICLE_LANGUAGE) -> str:
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
            TITLE_SYSTEM_MSG,
            user_prompt,
            max_tokens=OPENAI_MAX_TITLE_TOKENS,
            temperature=AI_TEMPERATURE_TITLE,
        )

    try:
        raw_text = _retry_with_backoff(_call_langchain_title)
    except Exception:
        logger.info("LangChain no disponible para título; usando SDK como fallback.")
        raw_text = None

    # 2) Fallback: OpenAI SDK Chat Completions — solo para modelos OpenAI/ChatGPT
    if not raw_text and not _is_gemini_model(OPENAI_MODEL) and client_ai is not None:
        def _call_chat():
            chat = client_ai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": TITLE_SYSTEM_MSG},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=AI_TEMPERATURE_TITLE,
                max_tokens=OPENAI_MAX_TITLE_TOKENS,
            )
            return chat.choices[0].message.content

        try:
            raw_text = _retry_with_backoff(_call_chat)
        except Exception as e:
            raise RuntimeError(f"Fallo generando título con OpenAI: {e}")

    if not raw_text:
        raise RuntimeError("El modelo no devolvió contenido para el título.")

    return raw_text.strip().strip("\"'").strip()[:META_TITLE_MAX_LENGTH]

def generate_and_save_article(
    client_ai: OpenAI | None,
    tag_text: str | None,
    parent_name: str,
    subcat_name: str,
    avoid_titles: list[str] | None = None,
    author_name: str = AUTHOR_USERNAME,
    site: str = SITE,
    language: str = ARTICLE_LANGUAGE,
    output_path: str = "article.json",
    title: str | None = None,
) -> bool:
    """Genera un artículo con IA y lo guarda en un fichero JSON."""
    avoid_titles = list(avoid_titles) if avoid_titles else []

    # Opcional: enviar el prompt por email antes de generar con OpenAI
    if SEND_PROMPT_EMAIL:
        try:
            email_generation_prompt(parent_name, subcat_name, tag_text, avoid_titles=avoid_titles)
            notify("Prompt enviado por email", "Se envió el prompt de generación a la dirección configurada.", level="info", always_email=False)
        except Exception as e:
            notify("Error enviando prompt por email", str(e), level="warning", always_email=True)

    # Si el título se proporcionó como argumento, generar solo el cuerpo y usarlo directamente
    if title:
        t, s, b, kw = generate_article_with_ai(client_ai, parent_name, subcat_name, tag_text, avoid_titles=avoid_titles, language=language)
        # Reemplazar el título generado por el proporcionado
        title, summary, body, keywords = title, s, _replace_h1(b, title), kw
    else:
        max_attempts = MAX_TITLE_RETRIES
        title = summary = body = None
        keywords: list[str] = []

        # Fase 1: Generar el artículo completo (única llamada costosa a OpenAI)
        t, s, b, kw = generate_article_with_ai(client_ai, parent_name, subcat_name, tag_text, avoid_titles=avoid_titles, language=language)

        if not is_too_similar(t, avoid_titles, threshold=SIMILARITY_THRESHOLD_STRICT):
            title, summary, body, keywords = t, s, b, kw
        else:
            # Fase 2: El cuerpo del artículo es válido; sólo regenerar el título (llamadas ligeras)
            notify("Título similar detectado", f"Intento 1/{max_attempts}: '{t}'. Regenerando sólo el título...", level="warning", always_email=True)
            avoid_titles.append(t)
            for attempt in range(2, max_attempts + 1):
                new_t = generate_title_with_ai(client_ai, parent_name, subcat_name, tag_text, avoid_titles=avoid_titles, language=language)
                if not is_too_similar(new_t, avoid_titles, threshold=SIMILARITY_THRESHOLD_STRICT):
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
    meta_title = title[:META_TITLE_MAX_LENGTH].rstrip() if len(title) > META_TITLE_MAX_LENGTH else title
    meta_description = summary[:META_DESCRIPTION_MAX_LENGTH].rstrip() if len(summary) > META_DESCRIPTION_MAX_LENGTH else summary
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
    parser.add_argument("--output", "-o", default="article.json",
                        help="Ruta del fichero JSON de salida")
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
    parser.add_argument("--avoid-titles", default="",
                        help="Títulos a evitar, separados por ';'")
    args = parser.parse_args()

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
