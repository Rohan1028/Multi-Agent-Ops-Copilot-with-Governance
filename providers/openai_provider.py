from __future__ import annotations

import os
from typing import Dict, Optional

import httpx

from app.config import Settings


class Provider:
    def __init__(self, settings: Settings) -> None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise RuntimeError('OPENAI_API_KEY not configured')
        self.settings = settings
        self.api_key = api_key
        self.api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1').rstrip('/')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.provider_name = 'openai'
        self._client = httpx.Client(base_url=self.api_base, timeout=10.0)
        self._last_usage: Optional[Dict[str, int]] = None

    def generate(self, prompt: str, system: str | None = None, max_tokens: int = 512) -> str:
        payload = {
            'model': self.model,
            'messages': [{'role': 'system', 'content': system or ''}, {'role': 'user', 'content': prompt}],
            'max_tokens': max_tokens,
        }
        response = self._client.post(
            '/chat/completions',
            headers={'Authorization': f'Bearer {self.api_key}'},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        usage = data.get('usage') or {}
        model_name = data.get('model', self.model)
        self._last_usage = {
            'prompt_tokens': usage.get('prompt_tokens', 0),
            'completion_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0),
            'model': model_name,
        }
        return data['choices'][0]['message']['content']

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens + output_tokens) / 100000

    def pop_last_usage(self) -> Optional[Dict[str, int]]:
        usage = self._last_usage
        self._last_usage = None
        return usage

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass
