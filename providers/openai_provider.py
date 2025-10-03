from __future__ import annotations

import os
from typing import Optional

import httpx

from app.config import Settings


class Provider:
    def __init__(self, settings: Settings) -> None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise RuntimeError('OPENAI_API_KEY not configured')
        self.settings = settings
        self.api_key = api_key
        self._client = httpx.Client(base_url='https://api.openai.com/v1', timeout=2.0)

    def generate(self, prompt: str, system: str | None = None, max_tokens: int = 512) -> str:
        payload = {
            'model': 'gpt-3.5-turbo',
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
        return data['choices'][0]['message']['content']

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens + output_tokens) / 100000

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass
