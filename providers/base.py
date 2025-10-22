from __future__ import annotations

import math
from dataclasses import dataclass, field
import json
from typing import Dict, Optional, Protocol

from app.config import Settings, get_settings


class BaseProvider(Protocol):
    def generate(self, prompt: str, system: str | None = None, max_tokens: int = 512) -> str: ...

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float: ...


class ProviderFactoryError(RuntimeError):
    pass


@dataclass
class StubProvider:
    settings: Settings
    model: str = "stub-001"
    provider_name: str = "stub"
    _last_usage: Optional[Dict[str, int]] = field(default=None, init=False, repr=False)

    def generate(self, prompt: str, system: str | None = None, max_tokens: int = 512) -> str:
        text: str
        if "[LLM_PLAN_REQUEST]" in prompt:
            plan = {
                "steps": [
                    {
                        "tool": "none",
                        "instruction": "Synthesize the knowledge base into a situational overview.",
                        "needs_approval": False,
                    },
                    {
                        "tool": "github",
                        "instruction": "Document work items and reviewers in GitHub referencing cited sources.",
                        "needs_approval": True,
                    },
                    {
                        "tool": "jira",
                        "instruction": "Update the Jira ticket with acceptance criteria and risk notes.",
                        "needs_approval": True,
                    },
                ]
            }
            text = json.dumps(plan)
        elif "[LLM_EXECUTOR_REQUEST]" in prompt:
            text = (
                "Action Summary:\n"
                "- Applied governance safe-guards.\n"
                "- Produced deliverable referencing cited sources.\n"
                "CITATIONS: ensure output embeds [source:...] tags."
            )
        elif "[LLM_REVIEW_REQUEST]" in prompt:
            text = "APPROVED: Output aligns with policy, citations present, no risk detected."
        else:
            seed = hash((prompt, system)) & 0xFFFF
            pseudo = (seed % 997) / 997
            text = f"[stub-response::{pseudo:.3f}] {prompt[: max_tokens // 2]}"

        prompt_tokens = max(1, len((prompt or "").split()))
        completion_tokens = max(1, len(text.split()))
        self._last_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        return text

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens + output_tokens) / 100000

    def pop_last_usage(self) -> Optional[Dict[str, int]]:
        usage = self._last_usage
        self._last_usage = None
        return usage


_DEFECTIVE = {
    'openai': 'providers.openai_provider',
    'azure': 'providers.azure_openai_provider',
}


def load_provider(name: str, settings: Settings | None = None) -> BaseProvider:
    settings = settings or get_settings()
    normalised = (name or 'stub').lower()
    if normalised in ('stub', 'default'):
        return StubProvider(settings)
    module_path = _DEFECTIVE.get(normalised)
    if not module_path:
        raise ProviderFactoryError(f'Unknown provider {name}')
    module = __import__(module_path, fromlist=['Provider'])
    provider_cls = getattr(module, 'Provider', None)
    if provider_cls is None:
        raise ProviderFactoryError(f'Provider module {module_path} missing Provider class')
    try:
        return provider_cls(settings=settings)
    except RuntimeError as exc:
        raise ProviderFactoryError(str(exc)) from exc
