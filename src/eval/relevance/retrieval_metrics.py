"""Ranked-retrieval metrics scored against graded qrels (H1/H2).

Per query, a retriever returns a ranked list of chunk_ids; we score it against
the qrels built from teacher labels:

  * Recall@k   — fraction of the relevant chunks (graded ≥ threshold) found in
                 the top k.
  * nDCG@k     — graded gain (2^rel − 1) discounted by log2(rank+1), normalised
                 by the ideal ordering of the *judged* chunks.
  * MRR        — reciprocal rank of the first relevant chunk.

Unjudged chunks count as relevance 0 (standard pooled-qrels assumption; the pool
was built to include every retriever's candidates, so misses are rare).
"""

from __future__ import annotations

import math
from collections.abc import Iterable


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return float("nan")  # undefined when a query has no relevant chunk
    hits = sum(1 for c in ranked[:k] if c in relevant)
    return hits / len(relevant)


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    for i, c in enumerate(ranked, 1):
        if c in relevant:
            return 1.0 / i
    return 0.0


def _dcg(gains: Iterable[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(ranked: list[str], graded: dict[str, int], k: int) -> float:
    """graded: {chunk_id: relevance}. Missing chunks are relevance 0."""
    gains = [2 ** graded.get(c, 0) - 1 for c in ranked[:k]]
    ideal = sorted((2 ** r - 1 for r in graded.values()), reverse=True)[:k]
    idcg = _dcg(ideal)
    if idcg == 0:
        return float("nan")  # no relevant judged chunk for this query
    return _dcg(gains) / idcg


def score_run(
    run: dict[str, list[str]],
    qrels: dict[str, dict[str, int]],
    relevant: dict[str, set[str]],
    ks: tuple[int, ...] = (5, 10),
) -> dict[str, float]:
    """Mean metrics over the queries present in BOTH the run and qrels.

    Queries with no relevant judged chunk are skipped per-metric (NaN-guarded),
    so they don't drag the mean.
    """
    queries = [q for q in run if q in qrels]
    out: dict[str, float] = {"n_queries": len(queries)}
    for k in ks:
        rec = [recall_at_k(run[q], relevant.get(q, set()), k) for q in queries]
        ndc = [ndcg_at_k(run[q], qrels[q], k) for q in queries]
        out[f"recall@{k}"] = _nanmean(rec)
        out[f"ndcg@{k}"] = _nanmean(ndc)
    out["mrr"] = _nanmean([reciprocal_rank(run[q], relevant.get(q, set())) for q in queries])
    return out


def _nanmean(xs: list[float]) -> float:
    vals = [x for x in xs if not math.isnan(x)]
    return sum(vals) / len(vals) if vals else float("nan")
