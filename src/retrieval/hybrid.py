"""Hybrid retriever: Reciprocal Rank Fusion of BM25 and dense rankings.

This is hypothesis H1 made concrete — combine a lexical (BM25) and a dense
(embedding) retriever and test whether the combination beats either alone.

Why RRF (Cormack, Clarke & Buettcher, 2009) rather than score averaging:
BM25 scores are unbounded and corpus-dependent; cosine similarities live in
[-1, 1]. Averaging them compares incomparable scales. RRF discards the raw
scores and fuses *ranks* only:

    rrf_score(d) = sum over retrievers r of  1 / (rrf_k + rank_r(d))

where rank_r(d) is d's 1-based position in retriever r's list (omitted if d
is absent from that list). rrf_k=60 is the canonical constant; RRF is famously
insensitive to it, so we do not tune it at this scale.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.retrieval.bm25_index import ScoredChunk


class Retriever(Protocol):
    """Anything that ranks chunks for a query (BM25Index, DenseIndex)."""

    def search(self, query: str, k: int) -> list[ScoredChunk]: ...


@dataclass(frozen=True)
class FusedChunk:
    """A chunk's fused result, with the component ranks that produced it.

    bm25_rank / dense_rank are 1-based, or None if the chunk was absent from
    that retriever's candidate list. Keeping them lets the eyeball check and
    the future annotation packet show *why* a chunk surfaced.
    """

    chunk_id: str
    rrf_score: float
    bm25_rank: int | None
    dense_rank: int | None


class HybridRetriever:
    """Fuse a lexical and a dense retriever with Reciprocal Rank Fusion."""

    def __init__(self, bm25: Retriever, dense: Retriever, rrf_k: int = 60) -> None:
        self._bm25 = bm25
        self._dense = dense
        self._rrf_k = rrf_k

    def search(
        self, query: str, k: int = 5, candidates_per_retriever: int = 20
    ) -> list[FusedChunk]:
        """Return the top-k fused chunks, highest RRF score first."""
        bm25_rank = self._ranks(self._bm25.search(query, candidates_per_retriever))
        dense_rank = self._ranks(self._dense.search(query, candidates_per_retriever))

        fused: list[FusedChunk] = []
        for cid in bm25_rank.keys() | dense_rank.keys():
            score = self._rrf_term(bm25_rank.get(cid)) + self._rrf_term(
                dense_rank.get(cid)
            )
            fused.append(
                FusedChunk(cid, score, bm25_rank.get(cid), dense_rank.get(cid))
            )
        fused.sort(key=lambda f: (-f.rrf_score, f.chunk_id))
        return fused[:k]

    @staticmethod
    def _ranks(results: list[ScoredChunk]) -> dict[str, int]:
        """Map chunk_id -> 1-based rank from an ordered result list."""
        return {sc.chunk_id: i + 1 for i, sc in enumerate(results)}

    def _rrf_term(self, rank: int | None) -> float:
        """RRF contribution of one retriever; 0 if the chunk was absent."""
        return 0.0 if rank is None else 1.0 / (self._rrf_k + rank)