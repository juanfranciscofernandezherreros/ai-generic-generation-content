# -*- coding: utf-8 -*-
import os, sys, json, random, re, unicodedata, difflib
import smtplib
from datetime import datetime, timezone, time, timedelta
from zoneinfo import ZoneInfo
from pymongo import MongoClient
from bson import ObjectId
from openai import OpenAI
from dotenv import load_dotenv
from email.message import EmailMessage

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
AUTHOR_USERNAME = os.getenv("AUTHOR_USERNAME") or "adminUser"  # fallback

# ============ HELPERS ============
def str_id(x):
    try:
        if isinstance(x, ObjectId):
            return str(x)
        return str(ObjectId(x)) if ObjectId.is_valid(str(x)) else str(x)
    except Exception:
        return str(x)

def as_list(v):
    if v is None: return []
    if isinstance(v, (list, tuple, set)): return list(v)
    return [v]

def tag_name(t):
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

# ========= Dominio categorías/tags =========
def get_related_tags_for_category(subcat, tags, tags_by_id, tags_by_name):
    related = []
    # claves directas
    for key in ("tags", "tagIds", "tagsIds"):
        if key in subcat:
            for raw in as_list(subcat.get(key)):
                sid = str_id(raw)
                if sid in tags_by_id:
                    related.append(tags_by_id[sid])
                else:
                    nm = str(raw)
                    if nm in tags_by_name:
                        related.append(tags_by_name[nm])

    if not related:
        sc_id = str_id(subcat.get("_id"))
        sc_name = str(subcat.get("name") or subcat.get("title") or sc_id)
        for t in tags:
            cand_ids = [t.get("categoryId"), t.get("category_id"), t.get("categoryRef")]
            cand_names = [t.get("categoryName"), t.get("category")]
            if any(str_id(cid) == sc_id for cid in cand_ids if cid is not None):
                related.append(t); continue
            if any(str(cn).strip() == sc_name for cn in cand_names if cn):
                related.append(t); continue
            for arr_key in ("categories", "categoryIds", "category_ids"):
                if arr_key in t:
                    arr = as_list(t.get(arr_key))
                    if any(str_id(x) == sc_id or str(x) == sc_name for x in arr):
                        related.append(t); break

    # únicos por _id
    seen, uniq = set(), []
    for t in related:
        k = str_id(t.get("_id"))
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    return uniq

def build_generation_prompt(parent_name: str, subcat_name: str, tag_text: str, avoid_titles=None) -> str:
    avoid_titles = avoid_titles or []
    avoid_block = ""
    if avoid_titles:
        avoid_list = [t.replace('"', '\\"') for t in avoid_titles[:5]]
        avoid_block = (
            "\\n- Evita usar títulos iguales o muy similares a cualquiera de estos: "
            + "; ".join(f'"{t}"' for t in avoid_list)
        )
    return f"""
Eres redactor técnico experto en Spring Boot y Lombok. Genera un artículo **en español** con la siguiente estructura JSON estricta:

{{
  "title": "...",
  "summary": "...",
  "body": "..."
}}

Reglas:
- El tema principal es "{tag_text}" dentro de la categoría "{parent_name}" y subcategoría "{subcat_name}".
- "title": atractivo, claro y conciso (máx. 70 caracteres).
- "summary": 2-3 frases que expliquen el valor del post.
- "body": HTML bien formado que incluya:
  - <h1> con el título (sin emojis en el h1).
  - Introducción breve (<p>).
  - 3-5 secciones <h2> con explicación técnica y buenas prácticas.
  - Cuando proceda, ejemplos de código reales en <pre><code class="language-..."> ... </code></pre>.
  - Una sección "Preguntas frecuentes (FAQ)" con 3-5 <h3> preguntas y respuestas <p>.
  - Una breve conclusión con llamada a la acción (CTA).
- El contenido debe ser original, correcto y usable.
- Si el tema encaja, incluye ejemplo práctico con Lombok y/o Spring Boot.
- Escapa correctamente comillas para que sea JSON válido.{avoid_block}
"""

def generate_article_with_ai(client_ai: OpenAI, parent_name: str, subcat_name: str, tag_text: str, avoid_titles=None):
    resp = client_ai.responses.create(
        model="gpt-5",
        input=build_generation_prompt(parent_name, subcat_name, tag_text, avoid_titles=avoid_titles)
    )
    raw = resp.output_text.strip()
    try:
        data = json.loads(raw)
    except Exception:
        start = raw.find("{"); end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = json.loads(raw[start:end+1])
        else:
            raise ValueError("La respuesta de OpenAI no es JSON válido:\n" + raw)

    title = str(data.get("title", "")).strip()
    summary = str(data.get("summary", "")).strip()
    body = str(data.get("body", "")).strip()
    if not title or not body:
        raise ValueError("Faltan 'title' o 'body' en la respuesta de OpenAI.")
    return title, summary, body

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

def send_notification_email(subject: str, html_body: str, text_body: str = None):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    pwd  = os.getenv("SMTP_PASS")
    from_email = os.getenv("FROM_EMAIL") or (user or "")
    to_email = os.getenv("NOTIFY_EMAIL") or "juanfranciscofernandezherreros@gmail.com"

    if not all([host, port, user, pwd, from_email, to_email]):
        print("⚠️ Faltan variables SMTP para enviar el correo. Se omite el envío.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    # Parte de texto (fallback) y HTML
    text_body = text_body or "Se ha publicado un nuevo artículo."
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, pwd)
            smtp.send_message(msg)
        print(f"📧 Notificación enviada a {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error enviando el correo: {e}", file=sys.stderr)
        return False

# ============ NUEVO: utilidades para 'mínimo 1 artículo por tag' ============
def build_hierarchy(categories):
    by_id = {str_id(c.get("_id")): c for c in categories}
    by_parent = {}
    for c in categories:
        pid = str_id(c.get("parent")) if c.get("parent") else None
        by_parent.setdefault(pid, []).append(c)
    return by_id, by_parent

def guess_parent_and_subcat_for_tag(tag, categories, by_id, by_parent):
    """Heurística para asociar un tag a (parent, subcategory).
    - Si el tag referencia una categoría concreta que es hija (tiene parent), usamos su parent y esa subcategoría.
    - Si referencia una categoría padre (sin parent), intentamos elegir una subcategoría hija.
    - Si no encontramos nada, caemos a una pareja aleatoria válida.
    """
    # 1) candidatos por id/nombre
    cand_ids = [tag.get("categoryId"), tag.get("category_id"), tag.get("categoryRef")]
    cand_names = [tag.get("categoryName"), tag.get("category")]
    arr_keys = ("categories", "categoryIds", "category_ids")

    # normaliza ids/nombres
    ids_norm = [str_id(x) for x in cand_ids if x]
    names_norm = [str(x).strip() for x in cand_names if x]

    # intenta por id directo
    for cid in ids_norm:
        c = by_id.get(cid)
        if c:
            parent_id = str_id(c.get("parent")) if c.get("parent") else None
            if parent_id:  # c es subcategoría
                return by_id.get(parent_id), c
            else:  # c es padre; elige una hija si existe
                children = by_parent.get(str_id(c.get("_id")), [])
                if children:
                    return c, random.choice(children)
            # sin hijas: continuar

    # intenta por nombre
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

    # intenta arrays de categorías
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

    # Fallback: pareja aleatoria válida (padre con al menos una hija)
    parent_candidates = [c for c in categories if str_id(c.get("_id")) in by_parent]
    if not parent_candidates:
        return None, None
    parent = random.choice(parent_candidates)
    children = by_parent.get(str_id(parent.get("_id")), [])
    subcat = random.choice(children) if children else None
    return parent, subcat

def get_recent_titles(db, limit=50):
    cur = db[ARTICLES_COLL].find({}, {"title": 1}).sort("createdAt", -1).limit(limit)
    titles = [d.get("title", "") for d in cur if d.get("title")]
    if len(titles) < limit:
        cur2 = db[ARTICLES_COLL].find({}, {"title": 1}).sort("_id", -1).limit(limit)
        titles2 = [d.get("title", "") for d in cur2 if d.get("title")]
        seen, final = set(), []
        for t in titles + titles2:
            if t not in seen:
                seen.add(t)
                final.append(t)
        return final[:limit]
    return titles

def ensure_article_for_tag(db, client_ai, tag, parent, subcat, recent_titles, author_id):
    """Genera e inserta un artículo para un tag si no existe ninguno. Devuelve True si creó algo."""
    tag_id = ObjectId(str_id(tag.get("_id")))

    # ¿ya existe al menos uno?
    exists = db[ARTICLES_COLL].find_one({"tags": tag_id})
    if exists:
        print(f"➡️  Ya existe artículo para tag '{tag_name(tag)}' (_id={tag_id}). Se omite.")
        return False

    parent_name = parent.get("name") if parent else str_id(parent.get("_id")) if parent else "General"
    subcat_name = subcat.get("name") if subcat else str_id(subcat.get("_id")) if subcat else "General"
    tag_text = tag_name(tag)

    # Evita títulos recientes muy parecidos
    avoid_titles = recent_titles[:10]

    max_attempts = 5
    attempt = 0
    title = summary = body = None

    while attempt < max_attempts:
        attempt += 1
        t, s, b = generate_article_with_ai(client_ai, parent_name, subcat_name, tag_text, avoid_titles=avoid_titles)
        if is_too_similar(t, recent_titles[:20], threshold=0.86):
            print(f"⚠️  Título similar detectado en intento {attempt}: '{t}'. Reintentando...")
            avoid_titles.append(t)
            continue
        title, summary, body = t, s, b
        break

    if not title or not body:
        print("❌ No se pudo generar un título suficientemente diferente tras varios intentos.", file=sys.stderr)
        return False

    base_slug = slugify(title)
    slug = next_available_slug(db, base_slug)
    now = now_utc()

    doc = {
        "title": title,
        "slug": slug,
        "summary": summary,
        "body": body,
        "category": ObjectId(str_id(subcat.get("_id"))) if subcat else None,
        "tags": [tag_id],
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
    }

    # Inserta
    res = db[ARTICLES_COLL].insert_one(doc)
    print(f"\n✅ Publicado en '{ARTICLES_COLL}' con _id = {res.inserted_id}")
    print(f"📰 Título: {title}")
    print(f"🔗 Slug:   {slug}")
    print(f"🏷️  Tag usado: {tag_text} (id={str_id(tag.get('_id'))})")

    # Notificación opcional por email
    subject = f"Nuevo artículo publicado: {title}"
    html_body = f"""
    <p>Hola,</p>
    <p>Se ha publicado un nuevo artículo:</p>
    <ul>
      <li><b>Título:</b> {title}</li>
      <li><b>Slug:</b> {SITE}/post/{slug}</li>
      <li><b>Fecha:</b> {now.isoformat()}</li>
    </ul>
    <p>Saludos.</p>
    """
    try:
        send_notification_email(subject, html_body, text_body=f"Se ha publicado: {title} (slug: {slug})")
    except Exception:
        # no interrumpe el flujo si falla el email
        pass

    # actualiza recientes para ayudar al siguiente tag
    recent_titles.insert(0, title)
    if len(recent_titles) > 50:
        del recent_titles[50:]
    return True

# ============ NUEVO: ventana "hoy" (Europa/Madrid) ============
def today_window_utc_for_madrid():
    """Devuelve (inicio_utc, fin_utc) del día actual en Europa/Madrid."""
    tz_madrid = ZoneInfo("Europe/Madrid")
    today_madrid = datetime.now(tz_madrid).date()
    start_madrid = datetime.combine(today_madrid, time(0, 0), tzinfo=tz_madrid)
    end_madrid = start_madrid + timedelta(days=1)
    return start_madrid.astimezone(timezone.utc), end_madrid.astimezone(timezone.utc)

# ============ MAIN ============
def main():
    # Validaciones de entorno mínimas
    missing = []
    if not OPENAIAPIKEY: missing.append("OPENAIAPIKEY")
    if not MONGODB_URI:  missing.append("MONGODB_URI")
    if not DB_NAME:      missing.append("DB_NAME")
    if not ARTICLES_COLL: missing.append("ARTICLES_COLL")
    if not USERS_COLL:    missing.append("USERS_COLL")
    if not CATEGORY_COLL: missing.append("CATEGORY_COLL")
    if not TAGS_COLL:     missing.append("TAGS_COLL")
    if missing:
        print("❌ Faltan variables de entorno: " + ", ".join(missing), file=sys.stderr)
        sys.exit(1)

    # Conexión a Mongo
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
    except Exception as e:
        print(f"❌ Error de conexión a MongoDB: {e}", file=sys.stderr)
        sys.exit(1)

    # ===== Limitar a 1 artículo por día (Europa/Madrid) =====
    try:
        start_utc, end_utc = today_window_utc_for_madrid()
        already_today = db[ARTICLES_COLL].count_documents({
            "publishDate": {"$gte": start_utc, "$lt": end_utc},
            "status": "published"
        })
        if already_today >= 1:
            print("🟨 Ya hay un artículo publicado hoy. Se cancela la ejecución.")
            sys.exit(0)   # cortar ejecución si ya hay uno hoy
    except Exception as e:
        print(f"❌ Error comprobando artículos de hoy: {e}", file=sys.stderr)
        sys.exit(1)

    # Carga básica necesaria para continuar
    try:
        categories = list(db[CATEGORY_COLL].find({}))
        tags = list(db[TAGS_COLL].find({}))
    except Exception as e:
        print(f"❌ Error consultando colecciones: {e}", file=sys.stderr)
        sys.exit(1)

    if not categories:
        print("No hay categorías en la colección.")
        return

    if not tags:
        print("No hay tags en la colección.")
        return

    # Autor
    try:
        author_id = find_author_id(db)
        print(f"👤 Autor encontrado: {AUTHOR_USERNAME} (id={author_id})")
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # Índices/jerarquía
    by_id, by_parent = build_hierarchy(categories)

    # Títulos recientes para control de parecido
    recent_titles = get_recent_titles(db, limit=50)

    # Cliente OpenAI
    client_ai = OpenAI(api_key=OPENAIAPIKEY)

    # Para no repetir siempre el mismo orden de tags
    random.shuffle(tags)

    created_count = 0
    for tag in tags:
        parent, subcat = guess_parent_and_subcat_for_tag(tag, categories, by_id, by_parent)
        if parent is None or subcat is None:
            print("⚠️ No se pudo deducir (padre, subcategoría) de forma fiable; se usará fallback aleatorio.")
            # (el propio guess ya hace fallbacks)

        try:
            created = ensure_article_for_tag(db, client_ai, tag, parent, subcat, recent_titles, author_id)
            if created:
                created_count += 1
                print("\n🟦 Límite diario alcanzado (1). Proceso detenido.")
                break   # solo 1 artículo por día
        except Exception as e:
            print(f"❌ Error generando/insertando para tag '{tag_name(tag)}': {e}", file=sys.stderr)
            continue

    print(f"\n🟩 Proceso terminado. Artículos creados: {created_count}")

if __name__ == "__main__":
    main()
