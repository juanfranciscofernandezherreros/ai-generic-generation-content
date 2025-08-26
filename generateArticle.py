import os, sys, json, random, re, unicodedata, difflib
import smtplib
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from openai import OpenAI
from dotenv import load_dotenv
from email.message import EmailMessage

# ============ CARGA .env ============
# Busca el .env en la carpeta actual del script
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# ============ CONFIG DESDE ENTORNO ============
MONGODB_URI    = os.getenv("MONGODB_URI")
DB_NAME        = os.getenv("DB_NAME")
CATEGORY_COLL  = os.getenv("CATEGORY_COLL")
TAGS_COLL      = os.getenv("TAGS_COLL")
USERS_COLL     = os.getenv("USERS_COLL")
ARTICLES_COLL  = os.getenv("ARTICLES_COLL")
OPENAIAPIKEY   = os.getenv("OPENAIAPIKEY")
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

def get_related_tags_for_category(subcat, tags, tags_by_id, tags_by_name):
    related = []
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
    seen, uniq = set(), []
    for t in related:
        k = str_id(t.get("_id"))
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    return uniq

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

def get_last_article(db):
    last = db[ARTICLES_COLL].find_one(sort=[("createdAt", -1)])
    if not last:
        last = db[ARTICLES_COLL].find_one(sort=[("_id", -1)])
    return last

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

def build_generation_prompt(parent_name: str, subcat_name: str, tag_text: str, avoid_titles=None) -> str:
    avoid_titles = avoid_titles or []
    avoid_block = ""
    if avoid_titles:
        avoid_list = [t.replace('"', '\\"') for t in avoid_titles[:5]]
        avoid_block = (
            "\\n- Evita usar títulos iguales o muy similares a cualquiera de estos: "
            + "; ".join(f"\"{t}\"" for t in avoid_list)
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

def now_utc():
    return datetime.now(tz=timezone.utc)

def find_author_id(db) -> ObjectId:
    """Busca el usuario fijo 'adminUser' en la colección de usuarios."""
    username = AUTHOR_USERNAME  # usa el de entorno si viene, si no "adminUser"
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
    from_email = os.getenv("FROM_EMAIL") or user
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

# ============ MAIN ============
def main():
    # Validaciones de entorno mínimas
    missing = []
    if not OPENAIAPIKEY: missing.append("OPENAIAPIKEY")
    if not MONGODB_URI:  missing.append("MONGODB_URI")
    if missing:
        print("❌ Faltan variables de entorno: " + ", ".join(missing), file=sys.stderr)
        sys.exit(1)

    # Conexión a Mongo
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        categories = list(db[CATEGORY_COLL].find({}))
        tags = list(db[TAGS_COLL].find({}))
    except Exception as e:
        print(f"❌ Error de conexión/consulta a MongoDB: {e}", file=sys.stderr)
        sys.exit(1)

    if not categories:
        print("No hay categorías en la colección.")
        return

    # Autor
    try:
        author_id = find_author_id(db)
        print(f"👤 Autor encontrado: {AUTHOR_USERNAME} (id={author_id})")
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    tags_by_id = {str_id(t.get("_id")): t for t in tags}
    tags_by_name = {tag_name(t): t for t in tags}

    # Jerarquía padre->subcategoría
    by_parent = {}
    for c in categories:
        pid = str_id(c.get("parent")) if c.get("parent") else None
        by_parent.setdefault(pid, []).append(c)

    parent_candidates = [c for c in categories if str_id(c.get("_id")) in by_parent]
    if not parent_candidates:
        print("No hay jerarquía padre->subcategoría. Asegúrate de usar el campo 'parent'.")
        return

    # Último artículo y títulos recientes
    last_article = get_last_article(db)
    last_tag_ids = set(str_id(x) for x in (last_article.get("tags", []) if last_article else []))
    last_title = last_article.get("title") if last_article else None
    recent_titles = get_recent_titles(db, limit=50)

    # Selección aleatoria con exclusión de último tag si es posible
    picked_parent = picked_subcat = picked_tag = None
    for _ in range(25):
        parent_cat = random.choice(parent_candidates)
        parent_id = str_id(parent_cat.get("_id"))
        children = by_parent.get(parent_id, [])
        if not children:
            continue
        subcat = random.choice(children)
        related = get_related_tags_for_category(subcat, tags, tags_by_id, tags_by_name) or \
                  get_related_tags_for_category(parent_cat, tags, tags_by_id, tags_by_name)
        if related:
            related_excl_last = [t for t in related if str_id(t.get("_id")) not in last_tag_ids]
            chosen_pool = related_excl_last if related_excl_last else related
            picked_parent, picked_subcat, picked_tag = parent_cat, subcat, random.choice(chosen_pool)
            break

    if not picked_tag:
        print("No se encontró combinación válida con tags.")
        return

    parent_name = picked_parent.get("name") or str_id(picked_parent.get("_id"))
    subcat_name = picked_subcat.get("name") or str_id(picked_subcat.get("_id"))
    tag_text = tag_name(picked_tag)

    print("✅ Selección aleatoria")
    print(f"   • Categoría:    {parent_name} (id={str_id(picked_parent.get('_id'))})")
    print(f"   • Subcategoría: {subcat_name} (id={str_id(picked_subcat.get('_id'))})")
    print(f"   • Tag:          {tag_text} (id={str_id(picked_tag.get('_id'))})")
    if last_article and last_tag_ids:
        print(f"   • Último tag publicado: {', '.join(last_tag_ids)} (evitado si fue posible)")

    # OpenAI desde entorno
    client_ai = OpenAI(api_key=OPENAIAPIKEY)
    max_attempts = 5
    attempt = 0
    title = summary = body = None

    avoid_titles = []
    if last_title:
        avoid_titles.append(last_title)
    avoid_titles.extend(recent_titles[:3])

    while attempt < max_attempts:
        attempt += 1
        t, s, b = generate_article_with_ai(client_ai, parent_name, subcat_name, tag_text, avoid_titles=avoid_titles)
        if is_too_similar(t, [last_title] if last_title else [], threshold=0.82) or \
           is_too_similar(t, recent_titles[:20], threshold=0.86):
            print(f"⚠️  Título similar detectado en intento {attempt}: '{t}'. Reintentando...")
            avoid_titles.append(t)
            continue
        title, summary, body = t, s, b
        break

    if not title or not body:
        print("❌ No se pudo generar un título suficientemente diferente tras varios intentos.", file=sys.stderr)
        sys.exit(1)

    # Documento final
    base_slug = slugify(title)
    slug = next_available_slug(db, base_slug)
    now = now_utc()

    doc = {
        "title": title,
        "slug": slug,
        "summary": summary,
        "body": body,
        "category": ObjectId(str_id(picked_subcat.get("_id"))),
        "tags": [ObjectId(str_id(picked_tag.get("_id")))],
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

    # Inserción en Mongo
    try:
        res = db[ARTICLES_COLL].insert_one(doc)
        print(f"\n✅ Publicado en '{ARTICLES_COLL}' con _id = {res.inserted_id}")
        print(f"📰 Título: {title}")
        print(f"🔗 Slug:   {slug}")
        print(f"🏷️  Tag usado: {tag_text} (id={str_id(picked_tag.get('_id'))})")
    except Exception as e:
        print(f"❌ Error insertando en MongoDB: {e}", file=sys.stderr)
        # Puedes notificar también el error por email si quieres
        return  # o sys.exit(1)

    # --- Notificación por email (solo después de inserción exitosa) ---
    subject = f"Nuevo artículo publicado: {title}"
    html_body = f"""
    <p>Hola,</p>
    <p>Se ha publicado un nuevo artículo:</p>
    <ul>
      <li><b>Título:</b> {title}</li>
      <li><b>Slug:</b> {slug}</li>
      <li><b>Fecha:</b> {now.isoformat()}</li>
    </ul>
    <p>Saludos.</p>
    """
    send_notification_email(subject, html_body, text_body=f"Se ha publicado: {title} (slug: {slug})")

if __name__ == "__main__":
    main()
