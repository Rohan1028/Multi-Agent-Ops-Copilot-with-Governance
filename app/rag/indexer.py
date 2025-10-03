from __future__ import annotations

import math
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from rank_bm25 import BM25Okapi


@dataclass
class IndexedCorpus:
    documents: List[str]
    sources: List[str]
    tokenized: List[List[str]]


class CorpusIndexer:
    "Builds and persists a BM25 index for the markdown corpus." 

    def __init__(self, corpus_dir: Path, index_path: Path, chunk_size: int = 180) -> None:
        self.corpus_dir = corpus_dir
        self.index_path = index_path
        self.chunk_size = chunk_size

    def build(self) -> IndexedCorpus:
        documents: List[str] = []
        sources: List[str] = []
        tokenized: List[List[str]] = []

        for md_file in sorted(self.corpus_dir.glob('*.md')):
            chunks = self._chunk_file(md_file)
            for idx, chunk in enumerate(chunks):
                documents.append(chunk)
                sources.append(f"{md_file.name}#chunk-{idx}")
                tokenized.append(self._tokenize(chunk))

        bm25 = BM25Okapi(tokenized)
        payload = {'documents': documents, 'sources': sources, 'tokenized': tokenized, 'idf': bm25.idf}
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with self.index_path.open('wb') as fh:
            pickle.dump(payload, fh)
        return IndexedCorpus(documents=documents, sources=sources, tokenized=tokenized)

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

    def _tokenize(self, text: str) -> List[str]:
        return [token.strip().lower() for token in text.split() if token.strip()]
