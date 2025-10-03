from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from app.config import get_settings

DEFAULT_POLICIES = '''
policies:
  tools:
    github:
      allowed_roles: [Executor, Reviewer]
      require_approval: true
      rate_limit_per_minute: 15
    jira:
      allowed_roles: [Executor]
      require_approval: true
      rate_limit_per_minute: 10
  review:
    enforce_citations: true
    reject_on_injection: true
    max_replans: 2
'''


class PolicyStore:
    def __init__(self, settings=None) -> None:
        self.settings = settings or get_settings()
        self.path = Path(self.settings.POLICY_PATH)
        self._cache = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            raw = yaml.safe_load(self.path.read_text(encoding='utf-8'))
        else:
            raw = yaml.safe_load(DEFAULT_POLICIES)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(DEFAULT_POLICIES, encoding='utf-8')
        return raw.get('policies', raw)

    def is_tool_allowed(self, role: str, tool: str) -> bool:
        allowed = self._cache.get('tools', {}).get(tool, {}).get('allowed_roles', [])
        return role in allowed

    def requires_approval(self, tool: str) -> bool:
        return bool(self._cache.get('tools', {}).get(tool, {}).get('require_approval', False))

    def rate_limit(self, tool: str) -> int:
        return int(self._cache.get('tools', {}).get(tool, {}).get('rate_limit_per_minute', 0))

    @property
    def review_config(self) -> Dict[str, Any]:
        return dict(self._cache.get('review', {}))
