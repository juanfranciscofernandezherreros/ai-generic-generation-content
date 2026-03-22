from __future__ import annotations

import json
import logging
import random
import re
import time as _time
from collections.abc import Callable
from typing import Any, Union

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

import config

logger = config.logger

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
    """Devuelve True si el proveedor es Google Gemini.

    Cuando ``AI_PROVIDER`` está definido como ``"gemini"`` se fuerza Gemini.
    Cuando es ``"openai"`` u ``"ollama"`` se descarta Gemini.
    Con ``"auto"`` (por defecto) se detecta por el nombre del modelo.
    """
    provider = config.AI_PROVIDER
    if provider == "gemini":
        return True
    if provider in ("openai", "ollama"):
        return False
    return model.lower().startswith("gemini")


def _is_ollama_provider() -> bool:
    """Devuelve True si el proveedor es Ollama (servidor local).

    Cuando ``AI_PROVIDER`` está definido como ``"ollama"`` se fuerza Ollama.
    Cuando es ``"openai"`` o ``"gemini"`` se descarta Ollama.
    Con ``"auto"`` (por defecto) se detecta por ``OLLAMA_BASE_URL``.
    """
    provider = config.AI_PROVIDER
    if provider == "ollama":
        return True
    if provider in ("openai", "gemini"):
        return False
    return bool(config.OLLAMA_BASE_URL)


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
    if _is_gemini_model(config.OPENAI_MODEL):
        llm = ChatGoogleGenerativeAI(
            model=config.OPENAI_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
    elif _is_ollama_provider():
        llm = ChatOpenAI(
            model=config.OPENAI_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            api_key=config.OLLAMA_PLACEHOLDER_API_KEY,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    else:
        llm = ChatOpenAI(
            model=config.OPENAI_MODEL,
            api_key=config.OPENAIAPIKEY,
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

# ========= Retry con back-off exponencial =========
def _retry_with_backoff(fn: Callable, max_retries: int = config.OPENAI_MAX_RETRIES, base_delay: float = config.OPENAI_RETRY_BASE_DELAY) -> Any:
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
