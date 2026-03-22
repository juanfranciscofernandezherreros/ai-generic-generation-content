from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

# ============ LOGGING ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logger = logging.getLogger("generateArticle")

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
