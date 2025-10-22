from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional

from app.config import Settings, get_settings


PRICING_USD_PER_MILLION = {
    ("openai", "gpt-4o-mini"): {"input": 0.15, "output": 0.60},
    ("openai", "gpt-4o-mini-high"): {"input": 0.6, "output": 2.40},
    ("openai", "gpt-4o"): {"input": 2.50, "output": 10.00},
    ("azure", "gpt-4o-mini"): {"input": 0.15, "output": 0.60},
    ("stub", "stub-001"): {"input": 0.0, "output": 0.0},
}

DEFAULT_PRICING = {"input": 0.2, "output": 0.8}

LLM_USAGE_TABLE = """
CREATE TABLE IF NOT EXISTS llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    latency_ms REAL NOT NULL,
    cost_usd REAL NOT NULL,
    created_at TEXT NOT NULL
);
"""


@dataclass
class UsageRecord:
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: float
    created_at: str


class LLMUsageLogger:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.db_path = Path(self.settings.DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(LLM_USAGE_TABLE)
            conn.commit()

    def _pricing(self, provider: str, model: str) -> Dict[str, float]:
        return PRICING_USD_PER_MILLION.get((provider.lower(), model.lower()), DEFAULT_PRICING)

    def calculate_cost(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = self._pricing(provider, model)
        cost = (
            (prompt_tokens / 1_000_000) * pricing["input"]
            + (completion_tokens / 1_000_000) * pricing["output"]
        )
        return round(cost, 6)

    def log_usage(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
    ) -> None:
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = self.calculate_cost(provider, model, prompt_tokens, completion_tokens)
        record = UsageRecord(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            created_at=datetime.utcnow().isoformat(),
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO llm_usage(provider, model, prompt_tokens, completion_tokens, total_tokens, latency_ms, cost_usd, created_at)
                VALUES (:provider, :model, :prompt_tokens, :completion_tokens, :total_tokens, :latency_ms, :cost_usd, :created_at)
                """,
                record.__dict__,
            )
            conn.commit()

    def recent(self, limit: int = 20) -> Iterable[UsageRecord]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT provider, model, prompt_tokens, completion_tokens, total_tokens, latency_ms, cost_usd, created_at "
                "FROM llm_usage ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        for row in rows:
            yield UsageRecord(*row)

    def summary(self) -> Dict[str, float]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(1), SUM(total_tokens), SUM(cost_usd), AVG(latency_ms) FROM llm_usage"
            ).fetchone()
        if not row or row[0] is None:
            return {"runs": 0, "tokens": 0.0, "cost_usd": 0.0, "avg_latency_ms": 0.0}
        runs, tokens, cost, latency = row
        return {
            "runs": int(runs),
            "tokens": float(tokens or 0.0),
            "cost_usd": round(float(cost or 0.0), 6),
            "avg_latency_ms": round(float(latency or 0.0), 2),
        }
