from __future__ import annotations

import os
from typing import Any

import httpx

from app.config import Settings
from app.governance.audit import AuditLogger


class GitHubRealClient:
    def __init__(self, settings: Settings, audit: AuditLogger) -> None:
        self.settings = settings
        self.audit = audit
        self.token = os.getenv('GITHUB_TOKEN')
        self.owner = os.getenv('GITHUB_REPO_OWNER')
        self.repo = os.getenv('GITHUB_REPO_NAME')
        if not self.is_configured(settings):
            raise RuntimeError('GitHub credentials not configured')
        self._client = httpx.Client(
            base_url='https://api.github.com',
            headers={'Authorization': f'token {self.token}', 'Accept': 'application/vnd.github+json'},
            timeout=httpx.Timeout(2.0, connect=2.0),
        )

    @staticmethod
    def is_configured(settings: Settings | None = None) -> bool:
        return all(
            os.getenv(env_key)
            for env_key in ['GITHUB_TOKEN', 'GITHUB_REPO_OWNER', 'GITHUB_REPO_NAME']
        )

    def execute_instruction(self, task, instruction: str) -> str:
        title = f"Ops Copilot: {getattr(task, 'title', 'task')}"
        body = instruction[:4000]
        try:
            response = self._client.post(
                f'/repos/{self.owner}/{self.repo}/issues',
                json={'title': title, 'body': body},
            )
            response.raise_for_status()
            data: Any = response.json()
            url = data.get('html_url', 'unknown')
            self.audit.log('GitHubRealClient', 'issue_created', {'url': url})
            return f'Created GitHub issue at {url}'
        except httpx.HTTPError as exc:
            self.audit.log('GitHubRealClient', 'api_error', {'status': getattr(exc.response, 'status_code', None)})
            return f'GitHub API error: {exc}'

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass
