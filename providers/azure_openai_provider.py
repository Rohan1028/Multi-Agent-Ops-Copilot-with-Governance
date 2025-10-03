from __future__ import annotations

import os

import httpx

from app.config import Settings


class Provider:
    def __init__(self, settings: Settings) -> None:
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        api_key = os.getenv('AZURE_OPENAI_API_KEY')
        deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')
        if not all([endpoint, api_key, deployment]):
            raise RuntimeError('Azure OpenAI configuration incomplete')
        self.settings = settings
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.deployment = deployment
        self._client = httpx.Client(timeout=2.0)

    def generate(self, prompt: str, system: str | None = None, max_tokens: int = 512) -> str:
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version=2023-07-01-preview"
        payload = {
            'messages': [
                {'role': 'system', 'content': system or ''},
                {'role': 'user', 'content': prompt},
            ],
            'max_tokens': max_tokens,
        }
        response = self._client.post(
            url,
            headers={'api-key': self.api_key, 'Content-Type': 'application/json'},
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
