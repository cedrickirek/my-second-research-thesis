"""Unit tests for the RRF hybrid retriever.

Fake retrievers return fixed rankings, so these tests pin the RRF math
exactly without needing real indexes.

Run: uv run pytest src/retrieval/ -q
"""

from src.retrieval.bm25_index import ScoredChunk
from src.retrieval.hybrid import FusedChunk, HybridRetriever


class _FakeRetriever:
    """Returns a fixed ranking. Scores are constant on purpose, to prove RRF
    uses *rank*, not score."""

    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        return [ScoredChunk(cid, 0.0) for cid in self._ids[:k]]


def test_consensus_top_ranks_first():
    # A is rank 1 in both retrievers -> highest RRF score.
    hybrid = HybridRetriever(
        _FakeRetriever(["A", "B", "C"]), _FakeRetriever(["A", "C", "B"])
    )
    results = hybrid.search("q", k=3)
    assert [f.chunk_id for f in results] == ["A", "B", "C"]


def test_rrf_score_matches_formula():
    hybrid = HybridRetriever(
        _FakeRetriever(["A", "B"]), _FakeRetriever(["B", "A"]), rrf_k=60
    )
    results = {f.chunk_id: f for f in hybrid.search("q", k=2)}
    # A: bm25 rank 1, dense rank 2 -> 1/61 + 1/62; B is symmetric -> equal.
    assert results["A"].rrf_score == 1 / 61 + 1 / 62
    assert results["B"].rrf_score == 1 / 61 + 1 / 62


def test_tie_breaks_by_chunk_id():
    hybrid = HybridRetriever(_FakeRetriever(["A", "B"]), _FakeRetriever(["B", "A"]))
    assert [f.chunk_id for f in hybrid.search("q", k=2)] == ["A", "B"]


def test_chunk_absent_from_one_retriever_has_none_rank():
    hybrid = HybridRetriever(_FakeRetriever(["A", "B"]), _FakeRetriever(["C"]))
    results = {f.chunk_id: f for f in hybrid.search("q", k=5)}
    assert results["C"].bm25_rank is None
    assert results["C"].dense_rank == 1
    assert results["A"].bm25_rank == 1
    assert results["A"].dense_rank is None


def test_records_component_ranks():
    hybrid = HybridRetriever(
        _FakeRetriever(["A", "B", "C"]), _FakeRetriever(["A", "B", "C"])
    )
    top = hybrid.search("q", k=1)[0]
    assert top.chunk_id == "A"
    assert top.bm25_rank == 1 and top.dense_rank == 1


def test_returns_fused_chunk_instances():
    hybrid = HybridRetriever(_FakeRetriever(["A"]), _FakeRetriever(["A"]))
    assert all(isinstance(f, FusedChunk) for f in hybrid.search("q"))