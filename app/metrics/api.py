from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from fastapi import APIRouter, Query

from app.config import get_settings

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    return sqlite3.connect(settings.DB_PATH)


@dataclass
class LLMUsagePoint:
    created_at: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: float


@router.get("/llm/timeseries")
def llm_timeseries(limit: int = Query(200, ge=1, le=1000)) -> Dict[str, List[Dict[str, object]]]:
    """Return LLM usage events ordered by timestamp for Grafana."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT created_at, provider, model, prompt_tokens, completion_tokens, total_tokens, latency_ms, cost_usd
            FROM llm_usage
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    points = [
        LLMUsagePoint(
            created_at=row[0],
            provider=row[1],
            model=row[2],
            prompt_tokens=row[3],
            completion_tokens=row[4],
            total_tokens=row[5],
            latency_ms=row[6],
            cost_usd=row[7],
        )
        for row in rows
    ]
    points.reverse()
    return {"points": [asdict(p) for p in points]}


@router.get("/governance/summary")
def governance_summary() -> Dict[str, object]:
    """Summaries for approvals, reviewer rejections, hallucination events."""
    with _connect() as conn:
        approvals = conn.execute(
            "SELECT status, COUNT(1) FROM approvals GROUP BY status"
        ).fetchall()
        audit = conn.execute(
            "SELECT action, COUNT(1) FROM audit_logs GROUP BY action"
        ).fetchall()
    approvals_map = {status: count for status, count in approvals}
    audit_map = {action: count for action, count in audit}
    return {
        "approvals": approvals_map,
        "audit": audit_map,
        "generated_at": datetime.utcnow().isoformat(),
    }
