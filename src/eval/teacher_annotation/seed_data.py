"""Seed the annotation DB from the real #12 pairs + the disp10 overlap design.

Builds, from the bundled ``data/`` files:

  SEED_ITEMS       one retrieval item per (query, chunk) pair, in a stable order
                   (grouped by query; chunks ordered by a hash of pair_id, so
                   the order is decorrelated from retrieval rank). The DB assigns
                   1-based ids in this order, which SEED_ASSIGNMENTS relies on.
  SEED_ANNOTATORS  teacher codes (T01..T10) from the assignment map.
  SEED_ASSIGNMENTS (code, item_id) for every pair of every query assigned to a
                   teacher (anchor + coverage) — realises the overlap design.

Variant-blind: ``retrieved_by`` / ``rank_hybrid`` are never loaded. ``source``
carries the ``pair_id`` (shown nowhere in the UI; present only in the export, so
labels can be rejoined to the full pair metadata downstream).

The whole evaluation corpus (all 1565 items) is seeded; the ``assignments`` table
is what restricts each teacher to their ~172 items.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from db import RETRIEVAL

DATA = Path(__file__).resolve().parent / "data"
PAIRS = DATA / "relevance_pairs.jsonl"
ASSIGN = DATA / "assignments_disp10.json"


def _stable_order(pair_id: str) -> str:
    return hashlib.md5(pair_id.encode("utf-8")).hexdigest()


def _pairs_by_query() -> dict[str, list[dict]]:
    by_q: dict[str, list[dict]] = {}
    for line in PAIRS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        p = json.loads(line)
        by_q.setdefault(p["query_id"], []).append(p)
    for items in by_q.values():
        items.sort(key=lambda p: _stable_order(p["pair_id"]))
    return by_q


def _build() -> tuple[list[dict], list[str], list[tuple[str, int]]]:
    by_q = _pairs_by_query()
    assign = json.loads(ASSIGN.read_text(encoding="utf-8"))

    seed_items: list[dict] = []
    item_id_of_pair: dict[str, int] = {}
    for qid in sorted(by_q):  # deterministic global order
        for p in by_q[qid]:
            item_id_of_pair[p["pair_id"]] = len(seed_items) + 1  # 1-based DB id
            seed_items.append(
                {
                    "item_type": RETRIEVAL,
                    "query": p["query_text"],
                    "content": p["chunk_text"],
                    "source": p["pair_id"],  # provenance; never shown to the teacher
                }
            )

    annotators = list(assign["per_teacher"].keys())
    seed_assignments: list[tuple[str, int]] = []
    for code, info in assign["per_teacher"].items():
        for qid in list(info["anchor_queries"]) + list(info["coverage_queries"]):
            for p in by_q[qid]:
                seed_assignments.append((code, item_id_of_pair[p["pair_id"]]))

    return seed_items, annotators, seed_assignments


SEED_ITEMS, SEED_ANNOTATORS, SEED_ASSIGNMENTS = _build()
