from __future__ import annotations

import os

import httpx

from app.config import Settings
from app.governance.audit import AuditLogger


class JiraRealClient:
    def __init__(self, settings: Settings, audit: AuditLogger) -> None:
        self.settings = settings
        self.audit = audit
        self.base_url = os.getenv('JIRA_BASE_URL')
        self.email = os.getenv('JIRA_EMAIL')
        self.token = os.getenv('JIRA_API_TOKEN')
        self.project_key = os.getenv('JIRA_PROJECT_KEY')
        if not self.is_configured(settings):
            raise RuntimeError('Jira credentials not configured')
        self._client = httpx.Client(timeout=httpx.Timeout(2.0, connect=2.0))

    @staticmethod
    def is_configured(settings: Settings | None = None) -> bool:
        return all(
            os.getenv(env_key)
            for env_key in ['JIRA_BASE_URL', 'JIRA_EMAIL', 'JIRA_API_TOKEN', 'JIRA_PROJECT_KEY']
        )

    def execute_instruction(self, task, instruction: str) -> str:
        url = f"{self.base_url.rstrip('/')}/rest/api/3/issue"
        payload = {
            'fields': {
                'project': {'key': self.project_key},
                'summary': getattr(task, 'title', 'Ops Copilot Task'),
                'description': instruction,
                'issuetype': {'name': 'Task'},
            }
        }
        try:
            response = self._client.post(
                url,
                auth=(self.email, self.token),
                json=payload,
                headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
            )
            response.raise_for_status()
            data = response.json()
            key = data.get('key', 'UNKNOWN')
            self.audit.log('JiraRealClient', 'ticket_created', {'key': key})
            return f'Created Jira ticket {key}'
        except httpx.HTTPError as exc:
            self.audit.log('JiraRealClient', 'api_error', {'status': getattr(exc.response, 'status_code', None)})
            return f'Jira API error: {exc}'

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass
