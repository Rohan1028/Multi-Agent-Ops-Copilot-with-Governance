from __future__ import annotations

import math
from dataclasses import dataclass
import json
from typing import Protocol

from app.config import Settings, get_settings


class BaseProvider(Protocol):
    def generate(self, prompt: str, system: str | None = None, max_tokens: int = 512) -> str: ...

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float: ...


class ProviderFactoryError(RuntimeError):
    pass


@dataclass
class StubProvider:
    settings: Settings

    def generate(self, prompt: str, system: str | None = None, max_tokens: int = 512) -> str:
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
            return json.dumps(plan)
        if "[LLM_EXECUTOR_REQUEST]" in prompt:
            return (
                "Action Summary:\n"
                "- Applied governance safe-guards.\n"
                "- Produced deliverable referencing cited sources.\n"
                "CITATIONS: ensure output embeds [source:...] tags."
            )
        if "[LLM_REVIEW_REQUEST]" in prompt:
            return "APPROVED: Output aligns with policy, citations present, no risk detected."

        seed = hash((prompt, system)) & 0xFFFF
        pseudo = (seed % 997) / 997
        return f"[stub-response::{pseudo:.3f}] {prompt[: max_tokens // 2]}"

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens + output_tokens) / 100000


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
