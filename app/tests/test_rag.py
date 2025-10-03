from app.config import get_settings
from app.rag.retriever import CorpusRetriever, require_citations


def test_retriever_returns_expected_chunk():
    retriever = CorpusRetriever(get_settings())
    results = retriever.retrieve('pull request guidelines and reviewers')
    assert results, 'retriever should return at least one chunk'
    text, source = results[0]
    assert 'pull request' in text.lower()
    annotated = require_citations('Summary generated', results)
    assert '[source:' in annotated
    assert source in annotated
