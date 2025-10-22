from __future__ import annotations

import pickle
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.rag.indexer import CorpusIndexer

RetrieverResult = Tuple[str, str]


class CorpusRetriever:
    "Loads a persisted embedding index and surfaces top-k semantic matches for a query."

    def __init__(self, settings=None, top_k: int = 3) -> None:
        self.settings = settings or get_settings()
        self.top_k = top_k
        self._documents: List[str] = []
        self._sources: List[str] = []
        self._embeddings: np.ndarray = np.zeros((0, 1), dtype=np.float32)
        self._model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
        self._model: SentenceTransformer | None = None
        self._ensure_index()

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _ensure_index(self) -> None:
        index_path = Path(self.settings.RAG_INDEX_PATH)
        if not index_path.exists():
            corpus_dir = Path(__file__).resolve().parent.parent / 'data' / 'corpus'
            CorpusIndexer(corpus_dir, index_path).build()
        with index_path.open('rb') as fh:
            payload = pickle.load(fh)
        if 'embeddings' not in payload:
            corpus_dir = Path(__file__).resolve().parent.parent / 'data' / 'corpus'
            CorpusIndexer(corpus_dir, index_path).build()
            with index_path.open('rb') as fh:
                payload = pickle.load(fh)
        self._documents = payload['documents']
        self._sources = payload['sources']
        self._embeddings = np.asarray(payload['embeddings'], dtype=np.float32)
        self._model_name = payload.get('model_name', self._model_name)

    def retrieve(self, query: str, top_k: int | None = None) -> List[RetrieverResult]:
        query = (query or '').strip()
        if not query or not len(self._documents):
            return []
        top_k = top_k or self.top_k
        query_vector = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        scores = self._embeddings @ query_vector
        ranked = np.argsort(-scores)[:top_k]
        return [(self._documents[idx], self._sources[idx]) for idx in ranked]


def require_citations(text: str, retrieved: Sequence[RetrieverResult]) -> str:
    if not retrieved:
        return text
    cited = list(dict.fromkeys(source for _, source in retrieved))
    citation_tags = ' '.join(f"[source:{source}]" for source in cited)
    if citation_tags in text:
        return text
    return f"{text}\n{citation_tags}"
