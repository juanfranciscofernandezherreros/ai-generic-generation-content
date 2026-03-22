from __future__ import annotations

import difflib
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any


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
