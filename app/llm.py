from __future__ import annotations

import json
from typing import Any, Dict, Optional

from providers.base import BaseProvider


def call_llm(
    provider: Optional[BaseProvider],
    *,
    system: str,
    prompt: str,
    max_tokens: int = 512,
) -> str:
    """Execute a single-turn request against the configured provider."""
    if provider is None:
        return ""
    return provider.generate(prompt=prompt, system=system, max_tokens=max_tokens)


def load_json_safely(payload: str) -> Dict[str, Any]:
    """Best-effort JSON loader that tolerates trailing text from permissive models."""
    snippet = payload.strip()
    if not snippet:
        return {}
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        # Attempt to locate the first valid JSON object in the string.
        start = snippet.find("{")
        end = snippet.rfind("}") + 1
        if start != -1 and end != 0:
            try:
                return json.loads(snippet[start:end])
            except json.JSONDecodeError:
                return {}
        return {}
