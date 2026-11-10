"""Unit tests for the BM25 lexical retriever.

Run: uv run pytest src/retrieval/ -q
"""

import pytest

from src.corpus.metadata import Chunk, ChunkMetadata, ContentType
from src.retrieval.bm25_index import BM25Index, ScoredChunk
from src.retrieval.tokenizer_fr import FrenchTokenizer


def _chunk(chunk_id: str, text: str) -> Chunk:
    meta = ChunkMetadata(
        chunk_id=chunk_id,
        subject="mathematics",
        level="Terminale C",
        topic="test",
        source="test",
        content_type=ContentType.THEORY,
        has_dropped_figure=False,
    )
    return Chunk(text=text, metadata=meta)


_TOK = FrenchTokenizer()
_CORPUS = [
    _chunk("c1", "La divisibilité dans Z et les multiples d'un entier relatif."),
    _chunk("c2", "Le théorème de Pythagore concerne les triangles rectangles."),
    _chunk("c3", "Un nombre premier a exactement deux diviseurs."),
]
_INDEX = BM25Index(_CORPUS, _TOK)


def test_relevant_chunk_ranks_first():
    assert _INDEX.search("théorème de Pythagore")[0].chunk_id == "c2"
    assert _INDEX.search("divisibilité et multiples")[0].chunk_id == "c1"
    assert _INDEX.search("diviseurs nombre premier")[0].chunk_id == "c3"


def test_top_k_limits_results():
    assert len(_INDEX.search("divisibilité", k=2)) == 2


def test_scores_are_descending():
    scores = [r.score for r in _INDEX.search("diviseurs nombre premier", k=3)]
    assert scores == sorted(scores, reverse=True)


def test_no_match_scores_zero_and_breaks_ties_by_id():
    results = _INDEX.search("automobile vacances", k=3)
    assert [r.chunk_id for r in results] == ["c1", "c2", "c3"]
    assert all(r.score == 0.0 for r in results)


def test_returns_scored_chunk_instances():
    assert all(isinstance(r, ScoredChunk) for r in _INDEX.search("divisibilité"))


def test_empty_corpus_raises():
    with pytest.raises(ValueError):
        BM25Index([], _TOK)