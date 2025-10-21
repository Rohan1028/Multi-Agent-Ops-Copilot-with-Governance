from __future__ import annotations

import pickle
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.rag.indexer import CorpusIndexer

RetrieverResult = Tuple[str, str]


class CorpusRetriever:
    "Loads a persisted BM25 index and surfaces top-k chunks for a query." 

    def __init__(self, settings=None, top_k: int = 3) -> None:
        self.settings = settings or get_settings()
        self.top_k = top_k
        self._index = None
        self._bm25: BM25Okapi | None = None
        self._ensure_index()

    def _ensure_index(self) -> None:
        index_path = Path(self.settings.RAG_INDEX_PATH)
        if not index_path.exists():
            corpus_dir = Path(__file__).resolve().parent.parent / 'data' / 'corpus'
            CorpusIndexer(corpus_dir, index_path).build()
        with index_path.open('rb') as fh:
            payload = pickle.load(fh)
        tokenized = payload['tokenized']
        self._bm25 = BM25Okapi(tokenized)
        self._bm25.idf = payload.get('idf', self._bm25.idf)
        self._documents = payload['documents']
        self._sources = payload['sources']

    def retrieve(self, query: str, top_k: int | None = None) -> List[RetrieverResult]:
        query = (query or '').strip()
        if not query:
            return []
        top_k = top_k or self.top_k
        tokens = [tok.lower() for tok in query.split() if tok.strip()]
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:top_k]
        return [(self._documents[idx], self._sources[idx]) for idx, _ in ranked]


def require_citations(text: str, retrieved: Sequence[RetrieverResult]) -> str:
    if not retrieved:
        return text
    cited = list(dict.fromkeys(source for _, source in retrieved))
    citation_tags = ' '.join(f"[source:{source}]" for source in cited)
    if citation_tags in text:
        return text
    return f"{text}\n{citation_tags}"
