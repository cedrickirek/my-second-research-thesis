"""Ingest returned teacher labels and build graded qrels (H1/H2 ground truth).

Accepts labels from either annotation tool:
  * static-HTML export  — JSONL with `pair_id`, `annotator_id`, `relevance`.
  * web-app export       — CSV  with `source` (=pair_id), `annotator_code`,
                           `relevance` (from `db.export_dataframe`).

Both normalise to records of (annotator, pair_id, query_id, chunk_id,
relevance). `pair_id` is `"{query_id}__{chunk_id}"`, so query/chunk are
recovered by splitting on the first `__` (neither id contains `__`).

`build_qrels` aggregates multiple raters on the same pair (the anchor) into one
graded 0-3 relevance per (query, chunk) by **round-half-up of the mean**;
relevance ≥ 2 is "relevant" for Recall (rubric v1.0 §seuil).
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

Label = dict  # {annotator, pair_id, query_id, chunk_id, relevance, notes}


def parse_pair_id(pair_id: str) -> tuple[str, str]:
    query_id, chunk_id = pair_id.split("__", 1)
    return query_id, chunk_id


def _label(annotator, pair_id, relevance, notes="") -> Label | None:
    if annotator is None or pair_id is None or relevance is None:
        return None
    try:
        rel = int(relevance)
    except (TypeError, ValueError):
        return None
    qid, cid = parse_pair_id(str(pair_id))
    return {
        "annotator": str(annotator),
        "pair_id": str(pair_id),
        "query_id": qid,
        "chunk_id": cid,
        "relevance": rel,
        "notes": (notes or ""),
    }


def load_labels(paths: list[Path | str]) -> list[Label]:
    """Load + normalise labels from any mix of .jsonl and .csv files.

    Labels with no relevance (ungraded items) are dropped.
    """
    out: list[Label] = []
    for path in paths:
        path = Path(path)
        if path.suffix.lower() == ".csv":
            with path.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    rel = row.get("relevance")
                    lab = _label(
                        row.get("annotator_code"),
                        row.get("source"),
                        rel if rel not in (None, "") else None,
                        row.get("comment", ""),
                    )
                    if lab:
                        out.append(lab)
        else:  # jsonl
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                lab = _label(
                    r.get("annotator_id"),
                    r.get("pair_id"),
                    r.get("relevance"),
                    r.get("notes", ""),
                )
                if lab:
                    out.append(lab)
    return out


def agreement_records(labels: list[Label]) -> list[tuple[str, str, int]]:
    """(unit=pair_id, rater=annotator, value=relevance) for the agreement module."""
    return [(la["pair_id"], la["annotator"], la["relevance"]) for la in labels]


def _round_half_up(x: float) -> int:
    return int(x + 0.5)


def build_qrels(labels: list[Label]) -> dict[str, dict[str, int]]:
    """Aggregate to {query_id: {chunk_id: graded_relevance 0-3}}.

    Multiple raters on a pair are averaged (round-half-up). A (query, chunk)
    with no label simply does not appear — unjudged, treated as non-relevant by
    the metrics, which is the standard pooled-qrels assumption.
    """
    by_pair: dict[tuple[str, str], list[int]] = defaultdict(list)
    for la in labels:
        by_pair[(la["query_id"], la["chunk_id"])].append(la["relevance"])
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    for (qid, cid), rels in by_pair.items():
        qrels[qid][cid] = _round_half_up(sum(rels) / len(rels))
    return dict(qrels)


def relevant_sets(
    qrels: dict[str, dict[str, int]], threshold: int = 2
) -> dict[str, set[str]]:
    """{query_id: {chunk_id with graded relevance >= threshold}} (Recall set)."""
    return {
        qid: {cid for cid, rel in chunks.items() if rel >= threshold}
        for qid, chunks in qrels.items()
    }
