"""Tests for label ingestion + qrels. Run: uv run pytest src/eval/relevance/test_qrels.py"""

import json

from src.eval.relevance.qrels import (
    build_qrels,
    load_labels,
    parse_pair_id,
    relevant_sets,
)


def test_parse_pair_id():
    assert parse_pair_id("syn-322-01__234-ciam-tc-0062") == (
        "syn-322-01",
        "234-ciam-tc-0062",
    )


def test_load_jsonl_and_csv_normalise_identically(tmp_path):
    jl = tmp_path / "disp10_T01_2026.jsonl"
    jl.write_text(
        json.dumps({"pair_id": "q1__c1", "annotator_id": "T01", "relevance": 3,
                    "notes": ""}) + "\n"
        + json.dumps({"pair_id": "q1__c2", "annotator_id": "T01", "relevance": None})
        + "\n",
        encoding="utf-8",
    )
    csv = tmp_path / "annotations.csv"
    csv.write_text(
        "annotator_code,source,relevance,comment\nT01,q1__c1,3,\n", encoding="utf-8"
    )
    jl_labels = load_labels([jl])
    csv_labels = load_labels([csv])
    # ungraded jsonl row dropped -> one label each, identical core fields
    assert len(jl_labels) == 1 and len(csv_labels) == 1
    for key in ("annotator", "pair_id", "query_id", "chunk_id", "relevance"):
        assert jl_labels[0][key] == csv_labels[0][key]
    assert jl_labels[0]["query_id"] == "q1" and jl_labels[0]["chunk_id"] == "c1"


def test_build_qrels_averages_raters_round_half_up():
    labels = [
        {"annotator": "T01", "pair_id": "q1__c1", "query_id": "q1", "chunk_id": "c1",
         "relevance": 2, "notes": ""},
        {"annotator": "T02", "pair_id": "q1__c1", "query_id": "q1", "chunk_id": "c1",
         "relevance": 3, "notes": ""},  # mean 2.5 -> 3
        {"annotator": "T01", "pair_id": "q1__c2", "query_id": "q1", "chunk_id": "c2",
         "relevance": 1, "notes": ""},
    ]
    qrels = build_qrels(labels)
    assert qrels["q1"]["c1"] == 3
    assert qrels["q1"]["c2"] == 1


def test_relevant_sets_threshold():
    qrels = {"q1": {"c1": 3, "c2": 2, "c3": 1, "c4": 0}}
    assert relevant_sets(qrels, threshold=2) == {"q1": {"c1", "c2"}}
    assert relevant_sets(qrels, threshold=3) == {"q1": {"c1"}}
