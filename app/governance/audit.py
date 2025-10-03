from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.config import get_settings

AUDIT_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    agent TEXT NOT NULL,
    action TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
'''

SENSITIVE_KEYS = {"token", "secret", "key", "password"}


def _mask_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    masked: Dict[str, Any] = {}
    for key, value in payload.items():
        if any(token in key.lower() for token in SENSITIVE_KEYS):
            masked[key] = "[masked]"
        elif isinstance(value, dict):
            masked[key] = _mask_payload(value)
        else:
            masked[key] = value
    return masked


class AuditLogger:
    def __init__(self, settings=None) -> None:
        self.settings = settings or get_settings()
        self.db_path = Path(self.settings.DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(AUDIT_TABLE_SQL)
            conn.commit()

    def log(self, agent: str, action: str, payload: Dict[str, Any]) -> None:
        safe_payload = json.dumps(_mask_payload(payload))
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit_logs(ts, agent, action, payload_json) VALUES (?, ?, ?, ?)",
                (datetime.utcnow().isoformat(), agent, action, safe_payload),
            )
            conn.commit()
