"""Unit tests for the #12 pair builder's pooling logic.

Fake retrievers return fixed rankings (same trick as test_hybrid /
test_instructional), so these pin the union / provenance / figure-filter logic
with no real index or model. Only bm25 + dense are wired here; hybrid and
instructional share the same union path and are exercised end-to-end by the
smoke run.
"""

from src.corpus.metadata import Chunk, ChunkMetadata, ContentType
from src.eval.relevance.build_pairs import RUBRIC_VERSION, build_pairs_for_query
from src.retrieval.bm25_index import ScoredChunk


class _FakeRetriever:
    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        return [ScoredChunk(cid, 0.0) for cid in self._ids[:k]]


def _chunk(cid: str, ctype: ContentType, *, figure: bool = False) -> Chunk:
    return Chunk(
        text=f"# {cid}",
        metadata=ChunkMetadata(
            chunk_id=cid,
            subject="mathematics",
            level="Terminale C",
            topic="t",
            source="s",
            content_type=ctype,
            has_dropped_figure=figure,
        ),
    )


_QUERY = {
    "query_id": "q1",
    "text": "une question",
    "bucket": "single_lecon",
    "question_type": "exercise",
    "lecons": ["6_ciam_tc"],
}


def _by_id() -> dict[str, Chunk]:
    return {
        "c1": _chunk("c1", ContentType.THEORY),
        "c2": _chunk("c2", ContentType.EXAMPLE),
        "c3": _chunk("c3", ContentType.THEORY, figure=True),
    }


def _run(include_figures: bool):
    return build_pairs_for_query(
        _QUERY,
        by_id=_by_id(),
        bm25=_FakeRetriever(["c1", "c2"]),
        pool_depth=10,
        dense=_FakeRetriever(["c2", "c3"]),
        include_figures=include_figures,
    )


def test_union_and_provenance():
    recs = {r["chunk_id"]: r for r in _run(include_figures=True)}
    assert set(recs) == {"c1", "c2", "c3"}
    assert recs["c1"]["retrieved_by"] == ["bm25"]
    assert recs["c2"]["retrieved_by"] == ["bm25", "dense"]  # found by both, deduped
    assert recs["c3"]["retrieved_by"] == ["dense"]


def test_figure_chunks_excluded_by_default():
    ids = {r["chunk_id"] for r in _run(include_figures=False)}
    assert ids == {"c1", "c2"}  # c3 has_dropped_figure -> dropped


def test_annotation_fields_blank_and_pair_id():
    rec = next(r for r in _run(include_figures=True) if r["chunk_id"] == "c2")
    assert rec["pair_id"] == "q1__c2"
    assert rec["relevance"] is None
    assert rec["annotator_id"] is None
    assert rec["rubric_version"] == RUBRIC_VERSION
    assert rec["chunk_text"] == "# c2"
    assert rec["query_lecons"] == ["6_ciam_tc"]
