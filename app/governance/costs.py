from __future__ import annotations

import math
from pathlib import Path
from typing import Dict

import yaml

from app.config import get_settings

DEFAULT_BUDGET = '''
run_budget_usd: 5.0
'''

DEFAULT_MODEL_CONFIG = '''
models:
  stub-001:
    input_per_1k: 0.0004
    output_per_1k: 0.0012
'''


class BudgetExceededError(RuntimeError):
    pass


class CostTracker:
    def __init__(self, settings=None, model: str = 'stub-001') -> None:
        self.settings = settings or get_settings()
        self.model = model
        self.budget = self._load_budget()
        self.pricing = self._load_pricing()
        self.total_cost = 0.0

    def _load_budget(self) -> float:
        path = Path(self.settings.BUDGET_PATH)
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding='utf-8'))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(DEFAULT_BUDGET, encoding='utf-8')
            data = yaml.safe_load(DEFAULT_BUDGET)
        return float(data.get('run_budget_usd', 5.0))

    def _load_pricing(self) -> Dict[str, Dict[str, float]]:
        path = Path(self.settings.MODEL_CONFIG_PATH)
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding='utf-8'))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(DEFAULT_MODEL_CONFIG, encoding='utf-8')
            data = yaml.safe_load(DEFAULT_MODEL_CONFIG)
        return data.get('models', {})

    def estimate_tokens(self, text: str) -> int:
        words = len((text or '').split())
        return max(1, int(math.ceil(words * 1.3)))

    def reset(self) -> None:
        self.total_cost = 0.0

    def track(self, prompt_text: str, response_text: str) -> float:
        pricing = self.pricing.get(self.model) or {'input_per_1k': 0.0004, 'output_per_1k': 0.0012}
        input_tokens = self.estimate_tokens(prompt_text)
        output_tokens = self.estimate_tokens(response_text)
        cost = (
            (input_tokens / 1000) * pricing.get('input_per_1k', 0)
            + (output_tokens / 1000) * pricing.get('output_per_1k', 0)
        )
        self.total_cost += cost
        if self.total_cost > self.budget:
            raise BudgetExceededError(
                f"Run cost exceeded budget: {self.total_cost:.4f} > {self.budget:.2f}"
            )
        return cost
