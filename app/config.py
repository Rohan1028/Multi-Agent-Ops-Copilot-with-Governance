from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from pydantic import Field
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = BASE_DIR / 'runtime'


class Settings(BaseSettings):
    """Centralised application configuration loaded from environment or defaults."""

    APP_ENV: str = Field(default='development')
    DB_PATH: Path = Field(default=RUNTIME_DIR / 'ops_copilot.sqlite')
    POLICY_PATH: Path = Field(default=RUNTIME_DIR / 'policies.yaml')
    BUDGET_PATH: Path = Field(default=RUNTIME_DIR / 'budget.yaml')
    MODEL_CONFIG_PATH: Path = Field(default=RUNTIME_DIR / 'model_config.yaml')
    RAG_INDEX_PATH: Path = Field(default=RUNTIME_DIR / 'rag_index.pkl')
    SANDBOX_REPO_PATH: Path = Field(default=BASE_DIR / 'sandbox_repo')
    LOG_LEVEL: str = Field(default='INFO')
    LLM_PROVIDER: str = Field(default='stub')

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False

    def ensure_runtime_paths(self) -> None:
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.BUDGET_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.MODEL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.RAG_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        Path(self.SANDBOX_REPO_PATH).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_paths()
    return settings


def read_optional_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}


def get_llm_provider(settings: Settings | None = None):
    from providers.base import ProviderFactoryError, load_provider

    settings = settings or get_settings()
    provider_name = (settings.LLM_PROVIDER or 'stub').lower()
    try:
        return load_provider(provider_name, settings)
    except ProviderFactoryError:
        return load_provider('stub', settings)
