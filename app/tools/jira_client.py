from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from app.config import get_settings
from app.governance.audit import AuditLogger


class JiraClientProtocol(Protocol):
    def execute_instruction(self, task, instruction: str) -> str: ...


class MockJiraClient:
    def __init__(self, path: Path, audit: AuditLogger) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.audit = audit

    def execute_instruction(self, task, instruction: str) -> str:
        record = {
            'task_id': getattr(task, 'id', 'unknown'),
            'instruction': instruction,
        }
        existing = []
        if self.path.exists():
            try:
                existing = json.loads(self.path.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                existing = []
        existing.append(record)
        self.path.write_text(json.dumps(existing, indent=2), encoding='utf-8')
        self.audit.log('MockJiraClient', 'ticket_update', record)
        return 'Logged Jira instruction for later execution'


# Lazy import for real integration

def get_jira_client(audit: AuditLogger, settings=None) -> JiraClientProtocol:
    settings = settings or get_settings()
    log_path = Path(settings.DB_PATH).with_suffix('.jira.json')

    try:
        from app.integrations.jira_real import JiraRealClient

        if JiraRealClient.is_configured(settings):
            return JiraRealClient(settings=settings, audit=audit)
    except Exception:  # pragma: no cover
        pass

    return MockJiraClient(path=log_path, audit=audit)
