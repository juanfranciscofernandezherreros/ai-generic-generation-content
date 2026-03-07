# -*- coding: utf-8 -*-
import math
import os, sys, json, random, re, unicodedata, difflib, logging
import smtplib
import time as _time
from datetime import datetime, timezone, time, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo
from pymongo import MongoClient
from pymongo.database import Database
from bson import ObjectId
from openai import OpenAI
from dotenv import load_dotenv
from email.message import EmailMessage

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
MONGODB_URI     = os.getenv("MONGODB_URI")
DB_NAME         = os.getenv("DB_NAME")
CATEGORY_COLL   = os.getenv("CATEGORY_COLL")
TAGS_COLL       = os.getenv("TAGS_COLL")
USERS_COLL      = os.getenv("USERS_COLL")
ARTICLES_COLL   = os.getenv("ARTICLES_COLL")
SITE            = os.getenv("SITE") or ""
OPENAIAPIKEY    = os.getenv("OPENAIAPIKEY")
AUTHOR_USERNAME = os.getenv("AUTHOR_USERNAME") or "adminUser"
OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "gpt-5")

# Notificaciones
SMTP_HOST   = os.getenv("SMTP_HOST")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER")
SMTP_PASS   = os.getenv("SMTP_PASS")
FROM_EMAIL  = os.getenv("FROM_EMAIL") or (SMTP_USER or "")
TO_EMAIL    = os.getenv("NOTIFY_EMAIL") or "jnfz92@gmail.com"
NOTIFY_VERBOSE = (os.getenv("NOTIFY_VERBOSE", "true").lower() in ("1","true","yes","y"))
# Controla si se limita a 1 artículo por semana (true) o se permite publicar siempre (false)
LIMIT_PUBLICATION = (os.getenv("LIMIT_PUBLICATION", "true").lower() in ("1", "true", "yes", "y"))
# Si es true, enviará por email el prompt de generación antes de llamar a OpenAI
SEND_PROMPT_EMAIL = (os.getenv("SEND_PROMPT_EMAIL", "false").lower() in ("1", "true", "yes", "y"))

# ============ CONSTANTS ============
SIMILARITY_THRESHOLD_DEFAULT = 0.82   # umbral para is_too_similar genérico
SIMILARITY_THRESHOLD_STRICT  = 0.86   # umbral usado al reintentar títulos
MAX_TITLE_RETRIES            = 5      # intentos máx. para generar título único
RECENT_TITLES_LIMIT          = 50     # cuántos títulos recientes cargar
OPENAI_MAX_RETRIES           = 3      # reintentos para llamadas a OpenAI
OPENAI_RETRY_BASE_DELAY      = 2      # seg. base para backoff exponencial
MONGO_TIMEOUT_MS             = 5000   # serverSelectionTimeoutMS
META_TITLE_MAX_LENGTH        = 60     # máx. caracteres para metaTitle SEO
META_DESCRIPTION_MAX_LENGTH  = 160    # máx. caracteres para metaDescription SEO
MAX_AVOID_TITLES_IN_PROMPT   = 5      # máx. títulos a incluir en el prompt (mantiene prompts cortos)

# ============ HELPERS ============
def str_id(x: Any) -> str:
    try:
        if isinstance(x, ObjectId):
            return str(x)
        return str(ObjectId(x)) if ObjectId.is_valid(str(x)) else str(x)
    except Exception:
        return str(x)

def as_list(v: Any) -> list:
    if v is None: return []
    if isinstance(v, (list, tuple, set)): return list(v)
    return [v]

def tag_name(t: Dict[str, Any]) -> str:
    return str(t.get("name") or t.get("tag") or t.get("_id"))

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text

def next_available_slug(db, base_slug: str) -> str:
    slug = base_slug
    n = 2
    while db[ARTICLES_COLL].find_one({"slug": slug}):
        slug = f"{base_slug}-{n}"
        n += 1
    return slug

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

# ========= Notificaciones / logging =========
def send_notification_email(subject: str, html_body: str, text_body: str = None):
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, FROM_EMAIL, TO_EMAIL]):
        print("⚠️  Faltan variables SMTP para enviar el correo. Se omite el envío.")
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    text_body = text_body or "Notificación del proceso."
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
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

# ========= Batch preload para evitar N+1 queries =========
def preload_published_tag_ids(db: Database) -> Set[str]:
    """Devuelve el conjunto de tag _id (como str) que ya tienen artículos publicados."""
    pipeline = [
        {"$match": {"status": "published", "tags": {"$exists": True, "$ne": []}}},
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags"}},
    ]
    return {str(doc["_id"]) for doc in db[ARTICLES_COLL].aggregate(pipeline)}

def preload_published_category_ids(db: Database) -> Set[str]:
    """Devuelve el conjunto de category _id (como str) que ya tienen artículos publicados."""
    pipeline = [
        {"$match": {"status": "published", "category": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$category"}},
    ]
    return {str(doc["_id"]) for doc in db[ARTICLES_COLL].aggregate(pipeline)}

def preload_published_ids(db: Database) -> Tuple[Set[str], Set[str]]:
    """
    Devuelve (published_tag_ids, published_cat_ids) en una sola consulta usando $facet.
    Evita dos round-trips a MongoDB respecto a llamar por separado a
    preload_published_tag_ids + preload_published_category_ids.
    """
    pipeline = [
        {"$match": {"status": "published"}},
        {"$facet": {
            "tags": [
                {"$match": {"tags": {"$exists": True, "$ne": []}}},
                {"$unwind": "$tags"},
                {"$group": {"_id": "$tags"}},
            ],
            "categories": [
                {"$match": {"category": {"$exists": True, "$ne": None}}},
                {"$group": {"_id": "$category"}},
            ],
        }},
    ]
    result = list(db[ARTICLES_COLL].aggregate(pipeline))
    if not result:
        return set(), set()
    facet = result[0]
    published_tag_ids = {str(doc["_id"]) for doc in facet.get("tags", [])}
    published_cat_ids = {str(doc["_id"]) for doc in facet.get("categories", [])}
    return published_tag_ids, published_cat_ids

# ========= Retry con back-off exponencial =========
def _retry_with_backoff(fn: Callable, max_retries: int = OPENAI_MAX_RETRIES, base_delay: float = OPENAI_RETRY_BASE_DELAY) -> Any:
    """Ejecuta *fn()* con reintentos y back-off exponencial. Reintenta solo errores transitorios."""
    last_exc: Optional[Exception] = None
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

# ========= Dominio categorías/tags =========
def index_tags(tags):
    """Índices útiles de tags por _id y por nombre/tag."""
    by_id = {}
    by_name = {}
    for t in tags:
        tid = str_id(t.get("_id"))
        by_id[tid] = t
        nm = (t.get("name") or t.get("tag") or "").strip()
        if nm:
            by_name[nm] = t
    return by_id, by_name

def get_related_tags_for_category(cat_or_subcat, tags, tags_by_id, tags_by_name):
    """
    Devuelve los tags relacionados con una categoría o subcategoría.
    Acepta tanto nodos padre como hijos.
    """
    related = []
    # claves directas
    for key in ("tags", "tagIds", "tagsIds"):
        if key in cat_or_subcat:
            for raw in as_list(cat_or_subcat.get(key)):
                sid = str_id(raw)
                if sid in tags_by_id:
                    related.append(tags_by_id[sid])
                else:
                    nm = str(raw)
                    if nm in tags_by_name:
                        related.append(tags_by_name[nm])

    if not related:
        node_id = str_id(cat_or_subcat.get("_id"))
        node_name = str(cat_or_subcat.get("name") or cat_or_subcat.get("title") or node_id)
        for t in tags:
            cand_ids = [t.get("categoryId"), t.get("category_id"), t.get("categoryRef")]
            cand_names = [t.get("categoryName"), t.get("category")]
            if any(str_id(cid) == node_id for cid in cand_ids if cid is not None):
                related.append(t); continue
            if any(str(cn).strip() == node_name for cn in cand_names if cn):
                related.append(t); continue
            for arr_key in ("categories", "categoryIds", "category_ids"):
                if arr_key in t:
                    arr = as_list(t.get(arr_key))
                    if any(str_id(x) == node_id or str(x) == node_name for x in arr):
                        related.append(t); break

    # únicos por _id
    seen, uniq = set(), []
    for t in related:
        k = str_id(t.get("_id"))
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    return uniq

def build_generation_prompt(parent_name: str, subcat_name: str, tag_text: str, avoid_titles: Optional[List[str]] = None) -> str:
    avoid_titles = avoid_titles or []
    avoid_block = ""
    if avoid_titles:
        avoid_list = [t.replace('"', '\"') for t in avoid_titles[:MAX_AVOID_TITLES_IN_PROMPT]]
        avoid_block = (
            "\n- Evita usar títulos iguales o muy similares a cualquiera de estos: "
            + "; ".join(f'"{t}"' for t in avoid_list)
        )
    return f"""
Eres redactor técnico sénior especializado en desarrollo de software con Spring Boot y Lombok.
Genera un artículo **en español** devolviendo **únicamente** un objeto JSON con esta estructura:
{{
  "title": "...",
  "summary": "...",
  "body": "...",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}

Reglas de contenido:
- El tema principal es "{tag_text}" dentro de la categoría "{parent_name}" y subcategoría "{subcat_name}".
- "title": atractivo, claro, conciso (máx. 60 caracteres), optimizado para SEO. Incluye la palabra clave principal.
- "summary": 2-3 frases que expliquen el valor del artículo. Debe funcionar como meta-descripción SEO (máx. 160 caracteres).
- "keywords": lista de 3-7 palabras clave SEO relevantes para el artículo (en minúsculas, sin repetir el título exacto).
- "body": HTML semántico y bien formado que incluya:
  · <h1> con el título (sin emojis en el h1).
  · Introducción breve (<p>) que enganche al lector y presente el problema que resuelve el tema.
  · 3-5 secciones <h2> con explicación técnica, buenas prácticas y casos de uso reales.
  · Cuando proceda, ejemplos de código completos y funcionales en <pre><code class=\\"language-...\\"> ... </code></pre>.
  · Los ejemplos deben seguir las convenciones del framework y ser copiables directamente.
  · Una sección <h2> "Preguntas frecuentes (FAQ)" con 3-5 preguntas en <h3> y respuestas en <p>.
  · Una breve conclusión <h2> con resumen de puntos clave y llamada a la acción (CTA).
  · Usa listas (<ul>/<ol>) para enumerar ventajas, pasos o comparativas.

Reglas de calidad:
- Contenido 100 % original, técnicamente correcto y listo para publicar.
- Tono profesional pero accesible; evita relleno o frases genéricas.
- Si el tema encaja, incluye ejemplo práctico con Lombok y/o Spring Boot.
- Asegúrate de que el HTML no tenga etiquetas sin cerrar.
- Escapa correctamente comillas dentro de los valores para que el JSON sea válido.{avoid_block}
"""

def build_title_prompt(parent_name: str, subcat_name: str, tag_text: str, avoid_titles: Optional[List[str]] = None) -> str:
    """Construye un prompt ligero para generar únicamente el título de un artículo."""
    avoid_titles = avoid_titles or []
    avoid_block = ""
    if avoid_titles:
        avoid_list = [t.replace('"', '\\"') for t in avoid_titles[:MAX_AVOID_TITLES_IN_PROMPT]]
        avoid_block = (
            "\nEvita títulos iguales o muy similares a cualquiera de estos: "
            + "; ".join(f'"{t}"' for t in avoid_list)
        )
    return (
        f'Genera un título de artículo técnico en español para el tema "{tag_text}" '
        f'(categoría: "{parent_name}", subcategoría: "{subcat_name}").\n'
        f"Requisitos: atractivo, conciso (máx. {META_TITLE_MAX_LENGTH} caracteres), "
        f"optimizado para SEO, incluye la palabra clave principal.{avoid_block}\n"
        "Devuelve ÚNICAMENTE el texto del título, sin comillas ni texto adicional."
    )

def email_generation_prompt(parent_name: str, subcat_name: str, tag_text: str, avoid_titles=None):
    """
    Construye el prompt y lo envía por email usando SMTP ya configurado.
    NO intenta parsear ninguna respuesta de OpenAI (solo notifica).
    Devuelve el prompt por si quieres loguearlo.
    """
    prompt = build_generation_prompt(parent_name, subcat_name, tag_text, avoid_titles=avoid_titles)
    html = f"<h3>Prompt de generación</h3><p>Se envía el prompt que se usará con OpenAI:</p><pre style=\"white-space:pre-wrap; word-break:break-word;\">{html_escape(prompt)}</pre>"
    send_notification_email(subject="Prompt de generación", html_body=html, text_body=prompt)
    return prompt

def find_author_id(db) -> ObjectId:
    """Busca el usuario fijo 'adminUser' (o el de entorno) en la colección de usuarios."""
    username = AUTHOR_USERNAME
    query = {
        "$or": [
            {"username": {"$regex": f"^{username}$", "$options": "i"}},
            {"userName": {"$regex": f"^{username}$", "$options": "i"}},
            {"name": {"$regex": f"^{username}$", "$options": "i"}},
        ]
    }
    user = db[USERS_COLL].find_one(query)
    if not user:
        raise RuntimeError(f"No se encontró el usuario '{username}' en la colección '{USERS_COLL}'.")
    uid = user.get("_id")
    if not isinstance(uid, ObjectId):
        if not ObjectId.is_valid(str(uid)):
            raise RuntimeError(f"El _id del usuario '{username}' no es un ObjectId válido: {uid}")
        uid = ObjectId(str(uid))
    return uid

# ======== Cobertura / helpers ========
def tag_has_published_article(db, tag) -> bool:
    """True si ya existe al menos un artículo published para este tag."""
    try:
        tag_id = ObjectId(str_id(tag.get("_id")))
    except Exception:
        return False
    return db[ARTICLES_COLL].count_documents({"tags": tag_id, "status": "published"}) > 0

def category_has_published_article(db, category) -> bool:
    """True si ya existe al menos un artículo published para esta categoría/subcategoría."""
    try:
        cat_id = ObjectId(str_id(category.get("_id")))
    except Exception:
        return False
    return db[ARTICLES_COLL].count_documents({"category": cat_id, "status": "published"}) > 0

def find_categories_without_article(db, categories):
    """Devuelve categorías/subcategorías que aún no tienen artículos publicados."""
    return [c for c in categories if not category_has_published_article(db, c)]

# ============ Ventana "semana actual" (Europa/Madrid) ============
def current_week_window_utc_for_madrid(start_weekday: int = 1):
    tz_madrid = ZoneInfo("Europe/Madrid")
    today = datetime.now(tz_madrid).date()
    weekday = today.isoweekday()  # 1-7
    delta_days = (weekday - start_weekday) % 7
    start_local = datetime.combine(today - timedelta(days=delta_days), time(0, 0), tzinfo=tz_madrid)
    end_local = start_local + timedelta(days=7)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

def today_window_utc_for_madrid():
    tz_madrid = ZoneInfo("Europe/Madrid")
    today_madrid = datetime.now(tz_madrid).date()
    start_madrid = datetime.combine(today_madrid, time(0, 0), tzinfo=tz_madrid)
    end_madrid = start_madrid + timedelta(days=1)
    return start_madrid.astimezone(timezone.utc), end_madrid.astimezone(timezone.utc)

# ============ Auxiliares usados en main() ============
def build_hierarchy(categories):
    by_id = {str_id(c.get("_id")): c for c in categories}
    by_parent = {}
    for c in categories:
        pid = str_id(c.get("parent")) if c.get("parent") else None
        by_parent.setdefault(pid, []).append(c)
    return by_id, by_parent

def guess_parent_and_subcat_for_tag(tag, categories, by_id, by_parent):
    """Heurística para asociar un tag a (parent, subcategory)."""
    cand_ids = [tag.get("categoryId"), tag.get("category_id"), tag.get("categoryRef")]
    cand_names = [tag.get("categoryName"), tag.get("category")]
    arr_keys = ("categories", "categoryIds", "category_ids")

    ids_norm = [str_id(x) for x in cand_ids if x]
    names_norm = [str(x).strip() for x in cand_names if x]

    for cid in ids_norm:
        c = by_id.get(cid)
        if c:
            parent_id = str_id(c.get("parent")) if c.get("parent") else None
            if parent_id:
                return by_id.get(parent_id), c
            else:
                children = by_parent.get(str_id(c.get("_id")), [])
                if children:
                    return c, random.choice(children)

    for name in names_norm:
        for c in categories:
            if str(c.get("name") or c.get("title") or "").strip() == name:
                parent_id = str_id(c.get("parent")) if c.get("parent") else None
                if parent_id:
                    return by_id.get(parent_id), c
                else:
                    children = by_parent.get(str_id(c.get("_id")), [])
                    if children:
                        return c, random.choice(children)

    for key in arr_keys:
        if key in tag:
            for raw in as_list(tag.get(key)):
                cid = str_id(raw)
                c = by_id.get(cid)
                if c:
                    parent_id = str_id(c.get("parent")) if c.get("parent") else None
                    if parent_id:
                        return by_id.get(parent_id), c
                    else:
                        children = by_parent.get(str_id(c.get("_id")), [])
                        if children:
                            return c, random.choice(children)

    parent_candidates = [c for c in categories if str_id(c.get("_id")) in by_parent]
    if not parent_candidates:
        return None, None
    parent = random.choice(parent_candidates)
    children = by_parent.get(str_id(parent.get("_id")), [])
    subcat = random.choice(children) if children else None
    return parent, subcat

def find_subcats_with_tags(categories, by_parent, tags, tags_by_id, tags_by_name):
    """
    Devuelve lista de (parent_id, subcat, rel_tags) con:
      - Subcategorías (categorías con parent) que tengan tags relacionados.
      - Categorías SIN hijos pero con tags relacionados.
    """
    subcats_with_tags = []

    # 1) Subcategorías (tienen padre)
    for parent_id, subs in by_parent.items():
        if parent_id is None:
            continue
        for sc in subs:
            rel = get_related_tags_for_category(sc, tags, tags_by_id, tags_by_name)
            if rel:
                subcats_with_tags.append((parent_id, sc, rel))

    # 2) Categorías sin hijos con tags
    for c in categories:
        cid = str_id(c.get("_id"))
        if cid not in by_parent:
            rel = get_related_tags_for_category(c, tags, tags_by_id, tags_by_name)
            if rel:
                subcats_with_tags.append((None, c, rel))

    return subcats_with_tags

# ======= Selector ESTRICTO (optimizado con preload) =======
def pick_fresh_target_strict(db, categories, by_id, by_parent, tags, tags_by_id, tags_by_name,
                             published_tag_ids: Optional[Set[str]] = None,
                             published_cat_ids: Optional[Set[str]] = None):
    """
    Devuelve (parent, subcat, tag) cumpliendo:
      - tag SIN artículos publicados
      - subcategoría SIN artículos publicados
      - categoría padre (si existe) SIN artículos publicados

    Usa conjuntos pre-cargados (published_tag_ids, published_cat_ids) para
    evitar consultas individuales a MongoDB (N+1).

    Si no hay ningún candidato con tag que cumpla, intenta publicación SIN tag:
      - subcategoría SIN artículos y padre SIN artículos (o categoría raíz SIN artículos)

    Si no hay nada que cumpla → (None, None, None).
    """
    # Pre-cargar si no se pasaron desde fuera
    if published_tag_ids is None:
        published_tag_ids = preload_published_tag_ids(db)
    if published_cat_ids is None:
        published_cat_ids = preload_published_category_ids(db)

    def _tag_has_article(tag_doc) -> bool:
        return str_id(tag_doc.get("_id")) in published_tag_ids

    def _cat_has_article(cat_doc) -> bool:
        return str_id(cat_doc.get("_id")) in published_cat_ids

    # 1) Con tags, cumpliendo regla estricta
    candidates = find_subcats_with_tags(categories, by_parent, tags, tags_by_id, tags_by_name)
    random.shuffle(candidates)
    for parent_id, subcat, rel_tags in candidates:
        parent = by_id.get(parent_id) if parent_id else None
        if subcat and _cat_has_article(subcat):
            continue
        if parent and _cat_has_article(parent):
            continue
        available_tags = [t for t in rel_tags if not _tag_has_article(t)]
        if not available_tags:
            continue
        random.shuffle(available_tags)
        t = random.choice(available_tags)
        return parent, subcat, t

    # 2) SIN tag — categorías/subcategorías sin artículos
    cats_wo_article = [c for c in categories if not _cat_has_article(c)]
    random.shuffle(cats_wo_article)
    for c in cats_wo_article:
        if c.get("parent"):
            parent = by_id.get(str_id(c.get("parent")))
            if parent and _cat_has_article(parent):
                continue
            return parent, c, None
        else:
            return c, None, None

    # 3) Nada
    return None, None, None

# ======== construir texto de tema ========
def build_topic_text(parent, subcat, tag):
    if tag:
        return tag_name(tag)
    if subcat and (subcat.get("name") or subcat.get("title")):
        return str(subcat.get("name") or subcat.get("title"))
    if parent and (parent.get("name") or parent.get("title")):
        return str(parent.get("name") or parent.get("title"))
    return "General"

def get_recent_titles(db: Database, limit: int = RECENT_TITLES_LIMIT) -> List[str]:
    """Obtiene los títulos más recientes con una sola consulta, usando _id como fallback de orden."""
    cur = db[ARTICLES_COLL].find(
        {"title": {"$exists": True, "$ne": ""}},
        {"title": 1, "createdAt": 1},
    ).sort([("createdAt", -1), ("_id", -1)]).limit(limit)
    return [d["title"] for d in cur]

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

def generate_article_with_ai(client_ai: OpenAI, parent_name: str, subcat_name: str, tag_text: str, avoid_titles: Optional[List[str]] = None) -> Tuple[str, str, str, List[str]]:
    """
    Llama a OpenAI para generar el artículo. Devuelve (title, summary, body, keywords).
    Soporta SDK nuevo (responses.create) y el anterior (chat.completions.create).
    Incluye reintentos con back-off exponencial para errores transitorios.
    """
    prompt = build_generation_prompt(parent_name, subcat_name, tag_text, avoid_titles=avoid_titles)

    raw_text = None

    # 1) Intento con API moderna (Responses) — con reintentos
    def _call_responses():
        resp = client_ai.responses.create(model=OPENAI_MODEL, input=prompt)
        text = getattr(resp, "output_text", None)
        if not text and hasattr(resp, "content") and resp.content:
            for c in resp.content:
                if getattr(c, "type", None) in (None, "output_text"):
                    text = getattr(c, "text", None)
                    if text:
                        break
        return text

    try:
        raw_text = _retry_with_backoff(_call_responses)
    except Exception:
        logger.info("API Responses no disponible; usando Chat Completions como fallback.")
        raw_text = None

    # 2) Fallback: Chat Completions — con reintentos
    if not raw_text:
        def _call_chat():
            chat = client_ai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Eres un redactor técnico que devuelve estrictamente JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            return chat.choices[0].message.content

        try:
            raw_text = _retry_with_backoff(_call_chat)
        except Exception as e:
            raise RuntimeError(f"Fallo llamando a OpenAI: {e}")

    if not raw_text:
        raise RuntimeError("OpenAI no devolvió contenido.")

    json_text = _extract_json_block(raw_text)
    data = _safe_json_loads(json_text)

    title = str(data.get("title", "")).strip()
    summary = str(data.get("summary", "")).strip()
    body = str(data.get("body", "")).strip()

    if not title or not body:
        raise ValueError("La respuesta de OpenAI no contiene 'title' y/o 'body'.")

    # Asegura <h1> acorde al título si falta
    if "<h1" not in body.lower():
        safe_title = html_escape(title)
        body = f'<h1>{safe_title}</h1>\n' + body

    raw_keywords = data.get("keywords", [])
    keywords: List[str] = (
        [str(k).strip() for k in raw_keywords if str(k).strip()]
        if isinstance(raw_keywords, list) else []
    )

    return title, summary, body, keywords

def generate_title_with_ai(client_ai: OpenAI, parent_name: str, subcat_name: str, tag_text: str, avoid_titles: Optional[List[str]] = None) -> str:
    """
    Genera únicamente el título del artículo con una llamada ligera a OpenAI.
    Mucho más económico que regenerar el artículo completo en cada reintento.
    """
    prompt = build_title_prompt(parent_name, subcat_name, tag_text, avoid_titles=avoid_titles)
    raw_text = None

    def _call_responses():
        resp = client_ai.responses.create(model=OPENAI_MODEL, input=prompt)
        text = getattr(resp, "output_text", None)
        if not text and hasattr(resp, "content") and resp.content:
            for c in resp.content:
                if getattr(c, "type", None) in (None, "output_text"):
                    text = getattr(c, "text", None)
                    if text:
                        break
        return text

    try:
        raw_text = _retry_with_backoff(_call_responses)
    except Exception:
        logger.info("API Responses no disponible; usando Chat Completions para título.")
        raw_text = None

    if not raw_text:
        def _call_chat():
            chat = client_ai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Eres un redactor técnico. Devuelve solo el título solicitado, sin comillas ni texto adicional."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.9,
            )
            return chat.choices[0].message.content

        try:
            raw_text = _retry_with_backoff(_call_chat)
        except Exception as e:
            raise RuntimeError(f"Fallo generando título con OpenAI: {e}")

    if not raw_text:
        raise RuntimeError("OpenAI no devolvió contenido para el título.")

    return raw_text.strip().strip("\"'").strip()[:META_TITLE_MAX_LENGTH]

def ensure_article_for_tag(db, client_ai, tag, parent, subcat, recent_titles, author_id):
    """Genera e inserta un artículo. Se asume que parent/subcat/tag ya cumplen la regla estricta."""
    tag_id = None
    existing_titles_for_tag = []

    if tag:
        try:
            tag_id = ObjectId(str_id(tag.get("_id")))
        except Exception:
            tag_id = None
        if tag_id:
            existing_for_tag = list(db[ARTICLES_COLL].find({"tags": tag_id}, {"title": 1}))
            existing_titles_for_tag = [d.get("title", "") for d in existing_for_tag if d.get("title")]

    parent_name = parent.get("name") if parent else (subcat.get("parentName") if subcat and subcat.get("parentName") else "General")
    subcat_name = subcat.get("name") if subcat else "General"
    topic_text = build_topic_text(parent, subcat, tag)

    # Evita títulos recientes y del mismo tag (si hay tag) — construir antes de enviar email o llamar a IA
    avoid_titles = (recent_titles[:10] if recent_titles else []) + existing_titles_for_tag[:20]
    # Lista combinada para la comprobación de similitud (evita dos iteraciones separadas)
    all_check_titles = (recent_titles[:20] if recent_titles else []) + existing_titles_for_tag

    # Opcional: enviar el prompt por email antes de generar con OpenAI
    if SEND_PROMPT_EMAIL:
        try:
            email_generation_prompt(parent_name, subcat_name, topic_text, avoid_titles=avoid_titles)
            notify("Prompt enviado por email", "Se envió el prompt de generación a la dirección configurada.", level="info", always_email=False)
        except Exception as e:
            notify("Error enviando prompt por email", str(e), level="warning", always_email=True)

    max_attempts = MAX_TITLE_RETRIES
    title = summary = body = None
    keywords: List[str] = []

    # Fase 1: Generar el artículo completo (única llamada costosa a OpenAI)
    t, s, b, kw = generate_article_with_ai(client_ai, parent_name, subcat_name, topic_text, avoid_titles=avoid_titles)

    if not is_too_similar(t, all_check_titles, threshold=SIMILARITY_THRESHOLD_STRICT):
        title, summary, body, keywords = t, s, b, kw
    else:
        # Fase 2: El cuerpo del artículo es válido; sólo regenerar el título (llamadas ligeras)
        notify("Título similar detectado", f"Intento 1/{max_attempts}: '{t}'. Regenerando sólo el título...", level="warning", always_email=True)
        avoid_titles.append(t)
        for attempt in range(2, max_attempts + 1):
            new_t = generate_title_with_ai(client_ai, parent_name, subcat_name, topic_text, avoid_titles=avoid_titles)
            if not is_too_similar(new_t, all_check_titles, threshold=SIMILARITY_THRESHOLD_STRICT):
                # Actualiza el <h1> del cuerpo para que coincida con el nuevo título
                escaped_title = html_escape(new_t)
                new_b, replacements = re.subn(r'<h1[^>]*>.*?</h1>', f'<h1>{escaped_title}</h1>', b, count=1, flags=re.DOTALL | re.IGNORECASE)
                if not replacements:
                    # El cuerpo no tenía <h1>; lo anteponemos
                    new_b = f'<h1>{escaped_title}</h1>\n' + b
                title, summary, body, keywords = new_t, s, new_b, kw
                break
            notify("Título similar detectado", f"Intento {attempt}/{max_attempts}: '{new_t}'. Reintentando...", level="warning", always_email=True)
            avoid_titles.append(new_t)

    if not title or not body:
        notify("No se pudo generar título único", "Tras varios intentos no se logró un título suficientemente diferente.", level="error", always_email=True)
        return False

    base_slug = slugify(title)
    slug = next_available_slug(db, base_slug)
    now = now_utc()

    word_count = count_words(body)
    reading_time = estimate_reading_time(body)
    meta_title = title[:META_TITLE_MAX_LENGTH].rstrip() if len(title) > META_TITLE_MAX_LENGTH else title
    meta_description = summary[:META_DESCRIPTION_MAX_LENGTH].rstrip() if len(summary) > META_DESCRIPTION_MAX_LENGTH else summary

    doc = {
        "title": title,
        "slug": slug,
        "summary": summary,
        "body": body,
        "category": (
            ObjectId(str_id(subcat.get("_id"))) if subcat
            else (ObjectId(str_id(parent.get("_id"))) if parent else None)
        ),
        "tags": [tag_id] if tag_id else [],
        "author": author_id,
        "status": "published",
        "likes": [],
        "favoritedBy": [],
        "isVisible": True,
        "publishDate": now,
        "generatedAt": now,
        "createdAt": now,
        "updatedAt": now,
        "images": None,
        "wordCount": word_count,
        "readingTime": reading_time,
        "keywords": keywords,
        "metaTitle": meta_title,
        "metaDescription": meta_description,
    }

    db[ARTICLES_COLL].insert_one(doc)
    where_txt = f"Tag: {tag_name(tag)}" if tag else f"Tema (categoría/subcat): {topic_text}"
    notify("Artículo publicado",
           f"Título: {title}<br>Slug: {SITE}/post/{slug if SITE else slug}<br>{where_txt}",
           level="success", always_email=True)

    recent_titles.insert(0, title)
    if len(recent_titles) > 50:
        del recent_titles[50:]
    return True

# ============ MAIN ============
def main():
    notify("Inicio de proceso", "Comenzando ejecución de publicación automática.", level="info", always_email=True)

    # Validaciones de entorno mínimas
    _required_env = {
        "OPENAIAPIKEY": OPENAIAPIKEY,
        "MONGODB_URI":  MONGODB_URI,
        "DB_NAME":      DB_NAME,
        "ARTICLES_COLL": ARTICLES_COLL,
        "USERS_COLL":    USERS_COLL,
        "CATEGORY_COLL": CATEGORY_COLL,
        "TAGS_COLL":     TAGS_COLL,
    }
    missing = [k for k, v in _required_env.items() if not v]

    if missing:
        msg = "Faltan variables de entorno: " + ", ".join(missing)
        notify("Configuración incompleta", msg, level="error", always_email=True)
        sys.exit(1)

    # Conexión a Mongo
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
        db = client[DB_NAME]
        notify("Conexión a MongoDB", f"Base de datos '{DB_NAME}' conectada correctamente.", level="success", always_email=True)
    except Exception as e:
        notify("Error de conexión a MongoDB", str(e), level="error", always_email=True)
        sys.exit(1)

    # ===== Control de límite semanal (Europa/Madrid, lunes-domingo) =====
    try:
        if LIMIT_PUBLICATION:
            start_utc, end_utc = current_week_window_utc_for_madrid(start_weekday=1)  # 1 = lunes
            already_this_week = db[ARTICLES_COLL].count_documents({
                "publishDate": {"$gte": start_utc, "$lt": end_utc},
                "status": "published"
            })

            if already_this_week >= 1:
                last_doc = db[ARTICLES_COLL].find(
                    {"publishDate": {"$gte": start_utc, "$lt": end_utc}, "status": "published"},
                    {"title": 1, "slug": 1, "publishDate": 1}
                ).sort("publishDate", -1).limit(1)
                last_article = next(iter(last_doc), None)
                if last_article:
                    last_title = last_article.get("title", "(sin título)")
                    last_slug  = last_article.get("slug", "")
                    last_date  = last_article.get("publishDate")
                    link = f"{SITE}/post/{last_slug}" if SITE and last_slug else last_slug
                    notify("Límite semanal alcanzado",
                           f"Ya existe al menos un artículo esta semana.<br><b>Título:</b> {last_title}<br><b>Slug:</b> {link}<br><b>Fecha:</b> {last_date.isoformat() if last_date else 'N/D'}",
                           level="warning", always_email=True)
                else:
                    notify("Límite semanal alcanzado", "Ya existe al menos un artículo esta semana (no se pudo recuperar el detalle).", level="warning", always_email=True)

                print("🟨 Ya hay un artículo publicado esta semana. Se cancela la ejecución (LIMIT_PUBLICATION=True).")
                sys.exit(0)
        else:
            notify("Límite semanal desactivado", "LIMIT_PUBLICATION=false → se permitirá publicación incluso si ya hay artículos esta semana.", level="info", always_email=True)
    except Exception as e:
        notify("Error comprobando límite semanal", str(e), level="error", always_email=True)
        sys.exit(1)

    # Carga básica necesaria para continuar
    try:
        categories = list(db[CATEGORY_COLL].find({}))
        tags = list(db[TAGS_COLL].find({}))
        notify("Datos cargados", f"Categorías: {len(categories)}; Tags: {len(tags)}.", level="info", always_email=True)
    except Exception as e:
        notify("Error consultando colecciones", str(e), level="error", always_email=True)
        sys.exit(1)

    if not categories:
        notify("Sin categorías", "No hay categorías en la colección.", level="warning", always_email=True)
        return

    # Autor
    try:
        author_id = find_author_id(db)
        notify("Autor encontrado", f"{AUTHOR_USERNAME} (id={author_id})", level="success", always_email=True)
    except Exception as e:
        notify("Autor no encontrado", str(e), level="error", always_email=True)
        sys.exit(1)

    # Índices/jerarquía
    by_id, by_parent = build_hierarchy(categories)
    tags_by_id, tags_by_name = index_tags(tags)

    # Títulos recientes para control de parecido
    recent_titles = get_recent_titles(db, limit=RECENT_TITLES_LIMIT)
    notify("Control de similitud", f"Títulos recientes cargados: {len(recent_titles)}", level="info", always_email=True)

    # Pre-cargar conjuntos de cobertura en una sola consulta $facet (evita N+1)
    published_tag_ids, published_cat_ids = preload_published_ids(db)
    logger.info("Cobertura pre-cargada — tags con artículo: %d, categorías con artículo: %d",
                len(published_tag_ids), len(published_cat_ids))

    # Cliente OpenAI
    try:
        client_ai = OpenAI(api_key=OPENAIAPIKEY)
        notify("OpenAI listo", f"Modelo: {OPENAI_MODEL}", level="info", always_email=True)
    except Exception as e:
        notify("Error inicializando OpenAI", str(e), level="error", always_email=True)
        sys.exit(1)

    # ===== Selección ESTRICTA (usa conjuntos pre-cargados) =====
    parent, subcat, tag = pick_fresh_target_strict(
        db, categories, by_id, by_parent, tags, tags_by_id, tags_by_name,
        published_tag_ids=published_tag_ids,
        published_cat_ids=published_cat_ids,
    )

    if not parent and not subcat and not tag:
        notify(
            "Sin destinos disponibles",
            "Regla estricta activada: todas las opciones de tag/categoría/subcategoría tienen al menos un artículo en alguno de los niveles. No se publicará nada.",
            level="warning",
            always_email=True
        )
        print("🟨 Cobertura detectada en algún nivel (tag/subcat/categoría). Proceso detenido.")
        sys.exit(0)

    sel_msg = (
        f"Parent: {parent.get('name') if parent else 'N/D'}; "
        f"Subcat: {subcat.get('name') if subcat else 'N/D'}; "
        f"{'Tag: ' + tag_name(tag) if tag else 'Sin tag (tema por categoría/subcategoría)'}"
    )
    notify("Selección realizada", sel_msg, level="info", always_email=True)

    # Publica exactamente 1 artículo (cumpliendo el límite semanal ya comprobado)
    created = False
    try:
        created = ensure_article_for_tag(db, client_ai, tag, parent, subcat, recent_titles, author_id)
    except Exception as e:
        notify("Error generando/insertando artículo", f"{('Tag ' + tag_name(tag)) if tag else 'Sin tag'} :: {e}", level="error", always_email=True)

    if created:
        notify("Proceso terminado", "Artículos creados: 1 (límite semanal alcanzado).", level="success", always_email=True)
        print("\n🟦 Límite semanal alcanzado (1). Proceso detenido.")
        print("\n🟩 Proceso terminado. Artículos creados: 1")
    else:
        notify("Proceso terminado", "Artículos creados: 0 (posiblemente ya existía un título muy similar).", level="warning", always_email=True)
        print("\n🟩 Proceso terminado. Artículos creados: 0")

if __name__ == "__main__":
    main()
