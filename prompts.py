from __future__ import annotations

import config
from utils import html_escape
from notifications import send_notification_email


def build_generation_prompt(parent_name: str, subcat_name: str, tag_text: str | None = None, title: str | None = None, avoid_titles: list[str] | None = None, language: str = config.ARTICLE_LANGUAGE) -> str:
    avoid_titles = avoid_titles or []
    avoid_block = ""
    if avoid_titles:
        avoid_list = [t.replace('"', '\"') for t in avoid_titles[:config.MAX_AVOID_TITLES_IN_PROMPT]]
        avoid_block = (
            "\nEvita títulos iguales o muy similares a: "
            + "; ".join(f'"{t}"' for t in avoid_list)
        )
    lang = config._language_name(language)
    topic = f'sobre "{tag_text}" ' if tag_text else ""
    if title:
        title_instruction = f'title: usa EXACTAMENTE este título: "{title}". No lo modifiques.'
    else:
        title_instruction = "title: optimizado para SEO y CTR, conciso (máx. 60 caracteres), incluye palabra clave principal al inicio."
    return f"""Artículo SEO en {lang} {topic}(categoría: "{parent_name}", subcategoría: "{subcat_name}").
Devuelve SOLO JSON: {{"title":"...","summary":"...","body":"...","keywords":[...]}}

{title_instruction}
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

def build_title_prompt(parent_name: str, subcat_name: str, tag_text: str | None = None, avoid_titles: list[str] | None = None, language: str = config.ARTICLE_LANGUAGE) -> str:
    """Construye un prompt ligero para generar únicamente el título de un artículo."""
    avoid_titles = avoid_titles or []
    avoid_block = ""
    if avoid_titles:
        avoid_list = [t.replace('"', '\\"') for t in avoid_titles[:config.MAX_AVOID_TITLES_IN_PROMPT]]
        avoid_block = (
            "\nEvita títulos iguales o muy similares a cualquiera de estos: "
            + "; ".join(f'"{t}"' for t in avoid_list)
        )
    lang = config._language_name(language)
    topic = f'para el tema "{tag_text}" ' if tag_text else ""
    return (
        f'Genera un título de artículo técnico en {lang} {topic}'
        f'(categoría: "{parent_name}", subcategoría: "{subcat_name}").\n'
        f"Requisitos: atractivo, conciso (máx. {config.META_TITLE_MAX_LENGTH} caracteres), "
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
