"""Unit tests for the instructional (composition) retriever.

Fake retrievers return a fixed fused ranking (same trick as test_hybrid), so
these pin the selection + fallback logic exactly, with no real index. Each
helper builds chunks whose only meaningful field is content_type.
"""

from src.corpus.metadata import Chunk, ChunkMetadata, ContentType
from src.retrieval.bm25_index import ScoredChunk
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.instructional import InstructionalRetriever


class _FakeRetriever:
    """Returns a fixed ranking; constant scores prove fusion uses rank."""

    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        return [ScoredChunk(cid, 0.0) for cid in self._ids[:k]]


def _chunk(cid: str, ctype: ContentType) -> Chunk:
    return Chunk(
        text=f"# {cid}",
        metadata=ChunkMetadata(
            chunk_id=cid,
            subject="mathematics",
            level="Terminale C",
            topic="t",
            source="s",
            content_type=ctype,
            has_dropped_figure=False,
        ),
    )


def _retriever(order: list[str], types: dict[str, ContentType]) -> InstructionalRetriever:
    """Build an InstructionalRetriever whose fused ranking == `order`.

    Both component retrievers return `order`, so RRF reproduces it exactly.
    """
    chunks = [_chunk(cid, types[cid]) for cid in order]
    hybrid = HybridRetriever(_FakeRetriever(order), _FakeRetriever(order))
    return InstructionalRetriever(hybrid, chunks)


def _ids(result) -> list[str]:
    return [c.metadata.chunk_id for c in result.selected]


def test_natural_composition_three_theory_two_example():
    order = ["t1", "t2", "e1", "t3", "e2", "t4"]
    types = {"t1": ContentType.THEORY, "t2": ContentType.THEOREM,
             "e1": ContentType.EXAMPLE, "t3": ContentType.DEFINITION,
             "e2": ContentType.EXAMPLE, "t4": ContentType.PROOF}
    res = _retriever(order, types).search("q")
    assert _ids(res) == ["t1", "t2", "e1", "t3", "e2"]  # fused-rank order
    assert res.n_theory == 3 and res.n_example == 2
    assert res.backfills == 0 and not res.fallback_fired
    assert res.example_available and res.n_example_in_pool == 2


def test_example_shortfall_backfills_with_theory():
    order = ["t1", "t2", "e1", "t3", "t4", "t5"]
    types = {c: (ContentType.EXAMPLE if c == "e1" else ContentType.THEORY) for c in order}
    res = _retriever(order, types).search("q")
    assert _ids(res) == ["t1", "t2", "e1", "t3", "t4"]
    assert res.n_theory == 4 and res.n_example == 1
    assert res.backfills == 1 and res.fallback_fired
    assert res.example_available and res.n_example_in_pool == 1


def test_no_examples_degrades_to_theory_only():
    order = ["t1", "t2", "t3", "t4", "t5"]
    types = {c: ContentType.THEORY for c in order}
    res = _retriever(order, types).search("q")
    assert len(res.selected) == 5 and res.n_example == 0
    assert res.backfills == 2 and res.fallback_fired
    assert not res.example_available and res.n_example_in_pool == 0


def test_exercise_is_never_selected():
    order = ["t1", "x1", "t2", "e1", "t3", "e2", "x2"]
    types = {"t1": ContentType.THEORY, "x1": ContentType.EXERCISE,
             "t2": ContentType.THEORY, "e1": ContentType.EXAMPLE,
             "t3": ContentType.THEORY, "e2": ContentType.EXAMPLE,
             "x2": ContentType.EXERCISE}
    res = _retriever(order, types).search("q")
    assert _ids(res) == ["t1", "t2", "e1", "t3", "e2"]
    assert "x1" not in _ids(res) and "x2" not in _ids(res)


def test_solution_counts_as_example():
    order = ["t1", "t2", "s1", "t3", "s2"]
    types = {"t1": ContentType.THEORY, "t2": ContentType.THEOREM,
             "s1": ContentType.SOLUTION, "t3": ContentType.DEFINITION,
             "s2": ContentType.SOLUTION}
    res = _retriever(order, types).search("q")
    assert _ids(res) == ["t1", "t2", "s1", "t3", "s2"]
    assert res.n_example == 2 and res.example_available


def test_theory_shortfall_backfills_with_examples():
    order = ["e1", "e2", "e3", "e4", "e5", "t1"]
    types = {c: (ContentType.THEORY if c == "t1" else ContentType.EXAMPLE) for c in order}
    res = _retriever(order, types).search("q")
    assert _ids(res) == ["e1", "e2", "e3", "e4", "t1"]
    assert res.n_theory == 1 and res.n_example == 4 and res.backfills == 2


def test_small_pool_returns_what_is_available():
    order = ["t1", "e1", "t2"]
    types = {"t1": ContentType.THEORY, "e1": ContentType.EXAMPLE, "t2": ContentType.THEORY}
    res = _retriever(order, types).search("q")
    assert _ids(res) == ["t1", "e1", "t2"]  # only 3 eligible -> returns 3, no crash
    assert res.backfills == 0
