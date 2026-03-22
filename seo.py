from __future__ import annotations

from typing import Any

import config


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
    language: str = config.ARTICLE_LANGUAGE,
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
