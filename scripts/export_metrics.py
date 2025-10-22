from __future__ import annotations

import csv
import json
from pathlib import Path
import sqlite3
from typing import Iterable, Tuple

from app.config import get_settings

OUTPUT_DIR = Path("reports/telemetry")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_llm_usage(conn: sqlite3.Connection) -> Iterable[Tuple]:
    cursor = conn.execute(
        "SELECT provider, model, prompt_tokens, completion_tokens, total_tokens, latency_ms, cost_usd, created_at "
        "FROM llm_usage ORDER BY id DESC"
    )
    yield from cursor.fetchall()


def fetch_approval_stats(conn: sqlite3.Connection) -> dict[str, int]:
    waiting = conn.execute("SELECT COUNT(1) FROM approvals WHERE status = 'pending'").fetchone()[0]
    approved = conn.execute("SELECT COUNT(1) FROM approvals WHERE status = 'approved'").fetchone()[0]
    rejected = conn.execute("SELECT COUNT(1) FROM approvals WHERE status = 'rejected'").fetchone()[0]
    return {"pending": waiting, "approved": approved, "rejected": rejected}


def fetch_audit_events(conn: sqlite3.Connection) -> dict[str, int]:
    cursor = conn.execute("SELECT action, COUNT(1) FROM audit_logs GROUP BY action")
    return {action: count for action, count in cursor.fetchall()}


def write_csv(path: Path, rows: Iterable[Tuple], header: Iterable[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def main() -> None:
    settings = get_settings()
    db_path = settings.DB_PATH
    with sqlite3.connect(db_path) as conn:
        usage_rows = list(fetch_llm_usage(conn))
        approval_stats = fetch_approval_stats(conn)
        audit_stats = fetch_audit_events(conn)

    write_csv(
        OUTPUT_DIR / "llm_usage.csv",
        usage_rows,
        ["provider", "model", "prompt_tokens", "completion_tokens", "total_tokens", "latency_ms", "cost_usd", "created_at"],
    )
    (OUTPUT_DIR / "approvals_summary.json").write_text(json.dumps(approval_stats, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "audit_summary.json").write_text(json.dumps(audit_stats, indent=2), encoding="utf-8")
    print(f"Exported metrics to {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
