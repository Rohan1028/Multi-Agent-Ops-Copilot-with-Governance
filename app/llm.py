from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from providers.base import BaseProvider

from app.metrics.llm_usage import LLMUsageLogger

_USAGE_LOGGER: LLMUsageLogger | None = None


def _get_usage_logger() -> LLMUsageLogger:
    global _USAGE_LOGGER
    if _USAGE_LOGGER is None:
        _USAGE_LOGGER = LLMUsageLogger()
    return _USAGE_LOGGER


def _pop_usage(provider: BaseProvider) -> Optional[Dict[str, int]]:
    popper = getattr(provider, "pop_last_usage", None)
    if callable(popper):
        return popper()
    return None


def call_llm(
    provider: Optional[BaseProvider],
    *,
    system: str,
    prompt: str,
    max_tokens: int = 512,
    usage_logger: Optional[LLMUsageLogger] = None,
) -> str:
    """Execute a single-turn request against the configured provider while capturing metrics."""
    if provider is None:
        return ""
    logger = usage_logger or _get_usage_logger()
    start = time.perf_counter()
    response = provider.generate(prompt=prompt, system=system, max_tokens=max_tokens)
    latency_ms = (time.perf_counter() - start) * 1000

    usage = _pop_usage(provider)
    if usage:
        provider_name = getattr(provider, "provider_name", provider.__class__.__name__.lower())
        model_name = usage.get("model") or getattr(provider, "model", "unknown")
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        if prompt_tokens or completion_tokens:
            logger.log_usage(
                provider=provider_name,
                model=str(model_name),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
            )

    return response


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
