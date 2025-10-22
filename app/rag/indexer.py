from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class IndexedCorpus:
    documents: List[str]
    sources: List[str]
    embeddings: List[List[float]]
    model_name: str


class CorpusIndexer:
    "Builds and persists a semantic embedding index for the markdown corpus."

    def __init__(
        self,
        corpus_dir: Path,
        index_path: Path,
        *,
        chunk_size: int = 180,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self.corpus_dir = corpus_dir
        self.index_path = index_path
        self.chunk_size = chunk_size
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def build(self) -> IndexedCorpus:
        documents: List[str] = []
        sources: List[str] = []

        for md_file in sorted(self.corpus_dir.glob('*.md')):
            chunks = self._chunk_file(md_file)
            for idx, chunk in enumerate(chunks):
                documents.append(chunk)
                sources.append(f"{md_file.name}#chunk-{idx}")

        if not documents:
            embeddings = np.zeros((0, 384), dtype=np.float32)
        else:
            embeddings = self.model.encode(documents, convert_to_numpy=True, normalize_embeddings=True)

        payload = {
            'documents': documents,
            'sources': sources,
            'embeddings': embeddings.tolist(),
            'model_name': self.model_name,
        }
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with self.index_path.open('wb') as fh:
            pickle.dump(payload, fh)
        return IndexedCorpus(
            documents=documents,
            sources=sources,
            embeddings=payload['embeddings'],
            model_name=self.model_name,
        )

    def _chunk_file(self, path: Path) -> Sequence[str]:
        text = path.read_text(encoding='utf-8')
        words = text.split()
        if not words:
            return ['']
        chunks = []
        for start in range(0, len(words), self.chunk_size):
            end = min(len(words), start + self.chunk_size)
            chunk_words = words[start:end]
            chunks.append(' '.join(chunk_words))
        return chunks
