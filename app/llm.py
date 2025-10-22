from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable, Optional

import httpx

from app.config import get_settings
from app.metrics.llm_usage import LLMUsageLogger
from app.llm_rate_limit import RateLimiter, RateLimitExceeded
from providers.base import BaseProvider, StubProvider

_USAGE_LOGGER: LLMUsageLogger | None = None
_RATE_LIMITER: RateLimiter | None = None


def _get_usage_logger() -> LLMUsageLogger:
    global _USAGE_LOGGER
    if _USAGE_LOGGER is None:
        _USAGE_LOGGER = LLMUsageLogger()
    return _USAGE_LOGGER


def _get_rate_limiter() -> RateLimiter:
    global _RATE_LIMITER
    if _RATE_LIMITER is None:
        _RATE_LIMITER = RateLimiter()
    return _RATE_LIMITER


def _pop_usage(provider: BaseProvider) -> Optional[Dict[str, int]]:
    popper = getattr(provider, "pop_last_usage", None)
    if callable(popper):
        return popper()
    return None


def _provider_name(provider: BaseProvider) -> str:
    return getattr(provider, "provider_name", provider.__class__.__name__.lower())


def _provider_model(provider: BaseProvider, usage: Dict[str, int] | None) -> str:
    if usage and "model" in usage:
        return str(usage["model"])
    return getattr(provider, "model", "unknown")


def call_llm(
    provider: Optional[BaseProvider],
    *,
    system: str,
    prompt: str,
    max_tokens: int = 512,
    usage_logger: Optional[LLMUsageLogger] = None,
    rate_limiter: Optional[RateLimiter] = None,
    rate_limit_keys: Iterable[str] | None = None,
    max_retries: int = 2,
    backoff_seconds: float = 1.0,
) -> str:
    """Execute a single-turn request against the configured provider while capturing metrics and enforcing rate limits."""
    if provider is None:
        return ""
    limiter = rate_limiter or _get_rate_limiter()
    logger = usage_logger or _get_usage_logger()
    keys = list(rate_limit_keys or [])
    attempt = 0
    last_exception: Exception | None = None

    while attempt <= max_retries:
        attempt += 1
        try:
            for key in keys:
                limiter.acquire(key, timeout=30.0)
            start = time.perf_counter()
            response = provider.generate(prompt=prompt, system=system, max_tokens=max_tokens)
            latency_ms = (time.perf_counter() - start) * 1000
            usage = _pop_usage(provider)
            if usage:
                provider_name = _provider_name(provider)
                model_name = _provider_model(provider, usage)
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
        except RateLimitExceeded as exc:
            last_exception = exc
            time.sleep(backoff_seconds)
        except httpx.HTTPStatusError as exc:
            last_exception = exc
            status = exc.response.status_code
            if status in {429, 500, 502, 503, 504} and attempt <= max_retries:
                time.sleep(backoff_seconds * attempt)
                continue
            break
        except httpx.HTTPError as exc:
            last_exception = exc
            if attempt <= max_retries:
                time.sleep(backoff_seconds * attempt)
                continue
            break
        except Exception as exc:
            last_exception = exc
            break

    # Fall back to stub provider to keep the pipeline moving
    try:
        fallback_provider = StubProvider(get_settings())
        return fallback_provider.generate(prompt=prompt, system=system, max_tokens=max_tokens)
    except Exception:
        if last_exception:
            raise last_exception
        raise


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
