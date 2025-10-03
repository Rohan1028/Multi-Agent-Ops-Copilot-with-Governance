from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from app.config import get_settings


APPROVAL_TABLE_SQL = '''
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    step_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
'''


@dataclass
class ApprovalRecord:
    step_id: str
    status: str
    created_at: str
    updated_at: str


class ApprovalRepository:
    def __init__(self, settings=None) -> None:
        self.settings = settings or get_settings()
        self.db_path = Path(self.settings.DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(APPROVAL_TABLE_SQL)
            conn.commit()

    def ensure(self, step_id: str) -> str:
        record = self.get(step_id)
        if record:
            return record.status
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO approvals(step_id, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (step_id, 'pending', now, now),
            )
            conn.commit()
        return 'pending'

    def get(self, step_id: str) -> Optional[ApprovalRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT step_id, status, created_at, updated_at FROM approvals WHERE step_id = ? ORDER BY id DESC LIMIT 1",
                (step_id,),
            ).fetchone()
        if not row:
            return None
        return ApprovalRecord(*row)

    def set_status(self, step_id: str, status: str) -> ApprovalRecord:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE approvals SET status = ?, updated_at = ? WHERE step_id = ?",
                (status, now, step_id),
            )
            conn.commit()
        record = self.get(step_id)
        if not record:
            raise ValueError(f"Approval record for {step_id} not found")
        return record

    def approve(self, step_id: str) -> ApprovalRecord:
        return self.set_status(step_id, 'approved')

    def reject(self, step_id: str) -> ApprovalRecord:
        return self.set_status(step_id, 'rejected')

    def pending(self) -> List[ApprovalRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT step_id, status, created_at, updated_at FROM approvals WHERE status = 'pending' ORDER BY created_at ASC"
            ).fetchall()
        return [ApprovalRecord(*row) for row in rows]
