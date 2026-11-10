"""Unit tests for the dense retriever.

A fake encoder maps known texts to fixed vectors, so these tests run offline
and never download the embedding model. The real model is exercised in the
end-to-end smoke run.

Run: uv run pytest src/retrieval/ -q
"""

import numpy as np
import pytest

from src.corpus.metadata import Chunk, ChunkMetadata, ContentType
from src.retrieval.bm25_index import ScoredChunk
from src.retrieval.dense_index import (
    E5_PREFIXES,
    NO_PREFIXES,
    DenseIndex,
    default_cache_path,
    model_slug,
    prefixes_for_model,
)


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


class _FakeEncoder:
    """Maps each input string to a fixed vector, then L2-normalizes."""

    def __init__(self, mapping: dict[str, list[float]]) -> None:
        self.mapping = mapping

    def encode(self, sentences, normalize_embeddings=True, convert_to_numpy=True):
        vecs = np.array([self.mapping[s] for s in sentences], dtype=float)
        if normalize_embeddings:
            vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs


_MAPPING = {
    "alpha": [1.0, 0.0, 0.0],
    "beta": [0.0, 1.0, 0.0],
    "gamma": [0.0, 0.0, 1.0],
    "q-beta": [0.2, 1.0, 0.0],  # closest to beta -> c2
    "q-tie": [1.0, 1.0, 1.0],  # equidistant to all three
}
_CORPUS = [_chunk("c1", "alpha"), _chunk("c2", "beta"), _chunk("c3", "gamma")]
# Empty prefixes so the fake mapping keys are the raw chunk texts.
_INDEX = DenseIndex(
    _CORPUS, model=_FakeEncoder(_MAPPING), query_prefix="", passage_prefix=""
)


def test_closest_vector_ranks_first():
    assert _INDEX.search("q-beta")[0].chunk_id == "c2"


def test_top_k_limits_results():
    assert len(_INDEX.search("q-beta", k=2)) == 2


def test_scores_descending_and_cosine_bounded():
    scores = [r.score for r in _INDEX.search("q-beta", k=3)]
    assert scores == sorted(scores, reverse=True)
    assert all(-1.0001 <= s <= 1.0001 for s in scores)


def test_tie_break_by_chunk_id():
    results = _INDEX.search("q-tie", k=3)
    assert [r.chunk_id for r in results] == ["c1", "c2", "c3"]


def test_returns_scored_chunk_instances():
    assert all(isinstance(r, ScoredChunk) for r in _INDEX.search("q-beta"))


def test_empty_corpus_raises():
    with pytest.raises(ValueError):
        DenseIndex([], model=_FakeEncoder(_MAPPING))


class _RaisingEncoder:
    """Fails if asked to encode — proves a code path didn't re-encode."""

    def encode(self, *args, **kwargs):
        raise RuntimeError("encode called")


def test_embeddings_cache_round_trip(tmp_path):
    cache = tmp_path / "emb.npz"
    idx1 = DenseIndex(
        _CORPUS,
        model=_FakeEncoder(_MAPPING),
        query_prefix="",
        passage_prefix="",
        embeddings_cache=cache,
    )
    assert cache.exists()
    # Cache hit: construction must load the matrix, never touch the encoder.
    idx2 = DenseIndex(
        _CORPUS,
        model=_RaisingEncoder(),
        query_prefix="",
        passage_prefix="",
        embeddings_cache=cache,
    )
    np.testing.assert_allclose(idx2._matrix, idx1._matrix)


def test_prefixes_inferred_by_model_family():
    assert prefixes_for_model("intfloat/multilingual-e5-large") == E5_PREFIXES
    assert prefixes_for_model("intfloat/multilingual-e5-small") == E5_PREFIXES
    assert prefixes_for_model("BAAI/bge-m3") == NO_PREFIXES


def test_unknown_model_defaults_to_no_prefix_with_warning(caplog):
    import logging

    with caplog.at_level(logging.WARNING):
        assert prefixes_for_model("some/unknown-model") == NO_PREFIXES
    assert any("unknown embedding model" in r.message for r in caplog.records)


def test_explicit_prefix_overrides_inference():
    # bge-m3 infers no prefix, but an explicit prefix must win.
    idx = DenseIndex(
        _CORPUS,
        model=_FakeEncoder(_MAPPING),
        model_name="BAAI/bge-m3",
        query_prefix="",
        passage_prefix="",
    )
    assert idx._query_prefix == ""


def test_model_slug_is_filesystem_safe():
    assert model_slug("intfloat/multilingual-e5-large") == "intfloat_multilingual-e5-large"
    assert model_slug("BAAI/bge-m3") == "BAAI_bge-m3"


def test_default_cache_path_is_per_model():
    p1 = default_cache_path("intfloat/multilingual-e5-large")
    p2 = default_cache_path("BAAI/bge-m3")
    assert p1 != p2
    assert p1.suffix == ".npz" and p1.name == "intfloat_multilingual-e5-large.npz"


def test_embeddings_cache_invalidated_on_corpus_change(tmp_path):
    cache = tmp_path / "emb.npz"
    DenseIndex(
        _CORPUS,
        model=_FakeEncoder(_MAPPING),
        query_prefix="",
        passage_prefix="",
        embeddings_cache=cache,
    )
    other = [_chunk("c1", "beta"), _chunk("c2", "gamma"), _chunk("c3", "alpha")]
    # Corpus changed -> key mismatch -> must recompute, so the raising encoder fires.
    with pytest.raises(RuntimeError):
        DenseIndex(
            other,
            model=_RaisingEncoder(),
            query_prefix="",
            passage_prefix="",
            embeddings_cache=cache,
        )
