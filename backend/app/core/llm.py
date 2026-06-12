"""Groq client factory + JSON-extraction helpers.

Nodes never construct a ChatGroq themselves; they call ``get_llm("assessor")``
so the model id is resolved from config in one place and can be swapped via env.
Groq's hosted API is free (no credit card), so a full run costs nothing.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from langchain_groq import ChatGroq

from app.core.config import get_settings

_MODELS = {
    "assessor": lambda s: s.assessor_model,
    "extractor": lambda s: s.extractor_model,
}


@lru_cache(maxsize=None)
def get_llm(role: str) -> ChatGroq:
    """Return a cached ChatGroq bound to the model configured for ``role``."""
    settings = get_settings()
    model = _MODELS.get(role, _MODELS["assessor"])(settings)
    return ChatGroq(
        model=model,
        api_key=settings.groq_api_key,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=120,
        # Both LLM roles must emit JSON; forcing JSON mode stops the smaller model
        # from occasionally returning prose/markdown that fails to parse.
        model_kwargs={"response_format": {"type": "json_object"}},
    )


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def strip_code_fences(text: str) -> str:
    """Remove a leading/trailing ```json ... ``` fence if the model added one."""
    text = text.strip()
    text = _FENCE_RE.sub("", text)
    return text.strip()


def extract_json(text: str) -> Any:
    """Parse JSON from a model response, tolerating code fences and prose around it.

    Raises ``ValueError`` if no valid JSON object/array can be recovered.
    """
    cleaned = strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end != -1 and end > start:
            snippet = cleaned[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not parse JSON from model output: {text[:200]!r}")
