"""
config.py
---------
Módulo de configuración centralizada del proyecto.

Responsabilidades:
- Carga las variables de entorno desde el fichero ``.env`` (vía ``python-dotenv``).
- Define todas las constantes de comportamiento del generador: umbrales de similitud,
  límites de reintentos, longitudes máximas de metadatos SEO, etc.
- Expone el ``logger`` compartido que usan todos los submódulos.
- Ofrece el mapa de idiomas soportados y la función auxiliar ``_language_name``.

Variables de entorno reconocidas:
    OPENAIAPIKEY                — Clave de API de OpenAI (obligatoria con modelos ``gpt-*``).
    GEMINI_API_KEY              — Clave de API de Google Gemini (obligatoria con modelos ``gemini-*``).
    OLLAMA_BASE_URL             — URL del servidor Ollama local (p. ej. ``http://localhost:11434/v1``).
    OPENAI_MODEL                — Nombre del modelo de IA (por defecto ``gpt-4o``).
    AI_PROVIDER                 — Proveedor de IA: ``auto`` | ``openai`` | ``gemini`` | ``ollama``.
    SITE                        — URL base del sitio web (p. ej. ``https://tusitio.com``).
    AUTHOR_USERNAME             — Nombre del autor de los artículos (por defecto ``adminUser``).
    ARTICLE_LANGUAGE            — Código ISO 639-1 del idioma (por defecto ``es``).
    AI_TEMPERATURE_ARTICLE      — Temperatura de generación del artículo (por defecto ``0.7``).
    AI_TEMPERATURE_TITLE        — Temperatura de generación del título (por defecto ``0.9``).
    OUTPUT_FILENAME             — Nombre del fichero JSON de salida (por defecto ``article.json``).
    SEND_EMAILS                 — Activar/desactivar envío de emails (por defecto ``true``).
    SMTP_HOST                   — Servidor SMTP para notificaciones.
    SMTP_PORT                   — Puerto SMTP (por defecto ``587``).
    SMTP_USER                   — Usuario SMTP.
    SMTP_PASS                   — Contraseña SMTP.
    FROM_EMAIL                  — Dirección de origen del email.
    NOTIFY_EMAIL                — Dirección de destino de las notificaciones.
    NOTIFY_VERBOSE              — Enviar emails detallados (por defecto ``true``).
    SEND_PROMPT_EMAIL           — Enviar el prompt por email antes de llamar a la IA (por defecto ``false``).
    SIMILARITY_THRESHOLD_DEFAULT — Umbral de similitud genérico (por defecto ``0.82``).
    SIMILARITY_THRESHOLD_STRICT  — Umbral de similitud estricto al reintentar títulos (por defecto ``0.86``).
    MAX_TITLE_RETRIES           — Intentos máximos para generar título único (por defecto ``5``).
    OPENAI_MAX_RETRIES          — Reintentos para llamadas a la API de IA (por defecto ``3``).
    OPENAI_RETRY_BASE_DELAY     — Segundos base para backoff exponencial (por defecto ``2``).
    META_TITLE_MAX_LENGTH       — Máximo de caracteres para metaTitle SEO (por defecto ``60``).
    META_DESCRIPTION_MAX_LENGTH — Máximo de caracteres para metaDescription SEO (por defecto ``160``).
    MAX_AVOID_TITLES_IN_PROMPT  — Máximo de títulos a incluir en el prompt (por defecto ``5``).
    OPENAI_MAX_ARTICLE_TOKENS   — Límite de tokens de salida para artículos (por defecto ``4096``).
    OPENAI_MAX_TITLE_TOKENS     — Límite de tokens de salida para títulos (por defecto ``100``).
    OLLAMA_PLACEHOLDER_API_KEY  — Clave ficticia para Ollama (por defecto ``ollama``).
    GENERATION_SYSTEM_MSG       — Mensaje de sistema para generación de artículos (sobrescribible).
    TITLE_SYSTEM_MSG            — Mensaje de sistema para generación de títulos (sobrescribible).
"""
from __future__ import annotations

import logging
import os
import re

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
# Proveedor de IA explícito: "openai", "gemini", "ollama" o "auto" (detección automática por modelo/URL)
AI_PROVIDER     = os.getenv("AI_PROVIDER", "auto").lower().strip()

# Nombre del fichero JSON de salida: se configura mediante la variable de entorno OUTPUT_FILENAME.
# Debe ser una ruta válida que termine en .json (p. ej. "article.json", "output/my-article.json").
# Si el valor no coincide con el patrón permitido, se usa "article.json" por defecto.
OUTPUT_FILENAME_PATTERN = re.compile(r"^[\w][\w.\-/]*\.json$")
_output_filename_env    = os.getenv("OUTPUT_FILENAME", "article.json")
if OUTPUT_FILENAME_PATTERN.match(_output_filename_env):
    OUTPUT_FILENAME = _output_filename_env
else:
    logger.warning(
        "OUTPUT_FILENAME='%s' no coincide con el patrón esperado (^[\\w][\\w.\\-/]*\\.json$). "
        "Usando 'article.json'.",
        _output_filename_env,
    )
    OUTPUT_FILENAME = "article.json"

# Notificaciones
SEND_EMAILS = (os.getenv("SEND_EMAILS", "true").lower() in ("1", "true", "yes", "y"))
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
SIMILARITY_THRESHOLD_DEFAULT = float(os.getenv("SIMILARITY_THRESHOLD_DEFAULT", "0.82"))   # umbral para is_too_similar genérico
SIMILARITY_THRESHOLD_STRICT  = float(os.getenv("SIMILARITY_THRESHOLD_STRICT",  "0.86"))   # umbral usado al reintentar títulos
MAX_TITLE_RETRIES            = int(os.getenv("MAX_TITLE_RETRIES",            "5"))         # intentos máx. para generar título único
OPENAI_MAX_RETRIES           = int(os.getenv("OPENAI_MAX_RETRIES",           "3"))         # reintentos para llamadas a OpenAI
OPENAI_RETRY_BASE_DELAY      = int(os.getenv("OPENAI_RETRY_BASE_DELAY",      "2"))         # seg. base para backoff exponencial
META_TITLE_MAX_LENGTH        = int(os.getenv("META_TITLE_MAX_LENGTH",        "60"))        # máx. caracteres para metaTitle SEO
META_DESCRIPTION_MAX_LENGTH  = int(os.getenv("META_DESCRIPTION_MAX_LENGTH",  "160"))       # máx. caracteres para metaDescription SEO
MAX_AVOID_TITLES_IN_PROMPT   = int(os.getenv("MAX_AVOID_TITLES_IN_PROMPT",   "5"))         # máx. títulos a incluir en el prompt (mantiene prompts cortos)
OPENAI_MAX_ARTICLE_TOKENS    = int(os.getenv("OPENAI_MAX_ARTICLE_TOKENS",    "4096"))      # límite de tokens de salida para artículos
OPENAI_MAX_TITLE_TOKENS      = int(os.getenv("OPENAI_MAX_TITLE_TOKENS",      "100"))       # límite de tokens de salida para títulos
OLLAMA_PLACEHOLDER_API_KEY   = os.getenv("OLLAMA_PLACEHOLDER_API_KEY", "ollama")          # clave ficticia para Ollama (no requiere autenticación)

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
_GENERATION_SYSTEM_MSG_DEFAULT = (
    "Eres redactor técnico sénior y experto en SEO especializado en tecnología y desarrollo de software. "
    "Generas contenido optimizado para motores de búsqueda con HTML semántico, "
    "estructura de encabezados jerárquica (h1 > h2 > h3), uso estratégico de palabras clave "
    "y metadatos precisos. "
    "El contenido que redactas está siempre relacionado con la categoría y el tag indicados en el prompt. "
    "Devuelves SOLO JSON válido con: title, summary, body (HTML semántico), keywords."
)
_TITLE_SYSTEM_MSG_DEFAULT = (
    "Eres experto en SEO técnico. "
    "Devuelve solo el título solicitado, sin comillas ni texto adicional."
)
GENERATION_SYSTEM_MSG = os.getenv("GENERATION_SYSTEM_MSG", _GENERATION_SYSTEM_MSG_DEFAULT)
TITLE_SYSTEM_MSG      = os.getenv("TITLE_SYSTEM_MSG",      _TITLE_SYSTEM_MSG_DEFAULT)
