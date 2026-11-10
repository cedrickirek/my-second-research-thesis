"""Tests for retrieval metrics. Run: uv run pytest src/eval/relevance/test_retrieval_metrics.py"""

import math

from src.eval.relevance.retrieval_metrics import (
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
    score_run,
)


def test_recall_at_k():
    ranked = ["c1", "c2", "c3", "c4"]
    relevant = {"c2", "c4"}
    assert recall_at_k(ranked, relevant, 2) == 0.5  # only c2 in top-2
    assert recall_at_k(ranked, relevant, 4) == 1.0
    assert math.isnan(recall_at_k(ranked, set(), 4))  # no relevant -> undefined


def test_reciprocal_rank():
    assert reciprocal_rank(["c1", "c2", "c3"], {"c2"}) == 0.5
    assert reciprocal_rank(["c1", "c2"], {"c1"}) == 1.0
    assert reciprocal_rank(["c1"], {"cX"}) == 0.0


def test_ndcg_perfect_and_imperfect_ordering():
    graded = {"c1": 3, "c2": 2, "c3": 0}
    # Ideal order -> nDCG 1.0
    assert math.isclose(ndcg_at_k(["c1", "c2", "c3"], graded, 3), 1.0, abs_tol=1e-9)
    # Reversed relevant items -> < 1
    assert ndcg_at_k(["c2", "c1", "c3"], graded, 3) < 1.0
    # No judged relevant chunk -> NaN
    assert math.isnan(ndcg_at_k(["x", "y"], {}, 3))


def test_ndcg_matches_hand_computation():
    # ranked c1(rel2), c2(rel0), c3(rel3); gains 3,0,7
    graded = {"c1": 2, "c2": 0, "c3": 3}
    dcg = 3 / math.log2(2) + 0 / math.log2(3) + 7 / math.log2(4)  # 3 + 0 + 3.5
    idcg = 7 / math.log2(2) + 3 / math.log2(3)  # ideal: rel3 then rel2
    assert math.isclose(ndcg_at_k(["c1", "c2", "c3"], graded, 3), dcg / idcg, abs_tol=1e-9)


def test_score_run_aggregates_over_shared_queries():
    run = {"q1": ["c1", "c2"], "q2": ["c3", "c4"], "qX": ["c9"]}
    qrels = {"q1": {"c1": 3, "c2": 0}, "q2": {"c4": 2}}
    relevant = {"q1": {"c1"}, "q2": {"c4"}}
    out = score_run(run, qrels, relevant, ks=(2,))
    assert out["n_queries"] == 2  # qX not in qrels
    assert 0.0 <= out["recall@2"] <= 1.0
    assert out["mrr"] == (1.0 + 0.5) / 2  # q1 first hit rank1, q2 rank2
