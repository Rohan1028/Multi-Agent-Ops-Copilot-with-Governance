from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from app.config import get_settings
from app.governance.audit import AuditLogger
from app.tools.sandbox_repo import SandboxRepo


class GitHubClientProtocol(Protocol):
    def execute_instruction(self, task, instruction: str) -> str: ...


class MockGitHubClient:
    def __init__(self, repo: SandboxRepo, log_path: Path, audit: AuditLogger) -> None:
        self.repo = repo
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.audit = audit

    def execute_instruction(self, task, instruction: str) -> str:
        entry = {
            'task_id': getattr(task, 'id', 'unknown'),
            'instruction': instruction,
        }
        previous = []
        if self.log_path.exists():
            try:
                previous = json.loads(self.log_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                previous = []
        previous.append(entry)
        self.log_path.write_text(json.dumps(previous, indent=2), encoding='utf-8')
        branch_name = f"task-{getattr(task, 'id', 'unknown')}"
        diff_file = self.repo.write_diff(branch_name, instruction)
        self.audit.log('MockGitHubClient', 'write_diff', {'branch': branch_name, 'diff': str(diff_file)})
        return f"Logged GitHub action for {branch_name}; diff at {diff_file}"


# Lazy import to avoid runtime cost when real adapters are absent

def get_github_client(audit: AuditLogger, settings=None) -> GitHubClientProtocol:
    settings = settings or get_settings()
    repo = SandboxRepo(Path(settings.SANDBOX_REPO_PATH))
    log_path = Path(settings.SANDBOX_REPO_PATH) / 'github_actions.json'

    try:
        from app.integrations.github_real import GitHubRealClient

        if GitHubRealClient.is_configured(settings):
            return GitHubRealClient(settings=settings, audit=audit)
    except Exception:  # pragma: no cover
        pass

    return MockGitHubClient(repo=repo, log_path=log_path, audit=audit)
