from __future__ import annotations

import math
import re

from utils import html_escape


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
