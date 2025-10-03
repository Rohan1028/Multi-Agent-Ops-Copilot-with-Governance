from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.rag.indexer import CorpusIndexer
from app.tools.sandbox_repo import SandboxRepo


def main() -> None:
    settings = get_settings()
    corpus_dir = Path(__file__).resolve().parents[1] / 'app' / 'data' / 'corpus'
    CorpusIndexer(corpus_dir, settings.RAG_INDEX_PATH).build()
    SandboxRepo(Path(settings.SANDBOX_REPO_PATH))
    print('Demo environment seeded: index built and sandbox repo initialised.')


if __name__ == '__main__':
    main()
