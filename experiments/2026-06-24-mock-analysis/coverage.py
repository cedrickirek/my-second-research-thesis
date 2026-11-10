"""How much gold-label coverage survives if we drop careless raters?

A (query, chunk) pair's gold relevance is the AVERAGE of every annotator who
graded it. Dropping a rater does NOT delete a pair as long as another rater also
graded it — the pair just loses that one vote. A pair only becomes an
'orphan' (unjudged -> treated as non-relevant) if EVERY rater who graded it is
dropped. Those orphans are exactly the gap a re-grade has to fill.

    uv run python experiments/2026-06-24-mock-analysis/coverage.py \
        --labels "experiments/annotated/clean_dedup/*.jsonl" --drop T07,T14
"""

from __future__ import annotations

import argparse
import glob
import statistics
from collections import defaultdict
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.qrels import load_labels  # noqa: E402


def qrels_from(labels):
    """{(qid,cid): rounded-mean relevance} over the given labels."""
    by_pair = defaultdict(list)
    for la in labels:
        by_pair[(la["query_id"], la["chunk_id"])].append(la["relevance"])
    return {k: int(statistics.mean(v) + 0.5) for k, v in by_pair.items()}


def summarize(qr, tag):
    queries = {q for (q, _) in qr}
    rel_pairs = {k for k, v in qr.items() if v >= 2}
    rel_queries = {q for (q, _) in rel_pairs}
    print(f"  {tag:<26} pairs judged={len(qr):4d}  queries judged={len(queries):3d}  "
          f"relevant pairs={len(rel_pairs):3d}  queries w/ a relevant chunk={len(rel_queries):3d}")
    return queries, set(qr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("--drop", default="", help="comma-separated rater codes to drop")
    args = ap.parse_args()

    labels = load_labels([Path(p) for p in glob.glob(args.labels)])
    drop = {d.strip() for d in args.drop.split(",") if d.strip()}
    keep_labels = [la for la in labels if la["annotator"] not in drop]

    base = qrels_from(labels)
    kept = qrels_from(keep_labels)

    print(f"\nBaseline raters: {sorted({la['annotator'] for la in labels})}")
    print(f"Dropping: {sorted(drop) or '(none)'}\n")
    base_q, base_pairs = summarize(base, "ALL raters (baseline):")
    kept_q, kept_pairs = summarize(kept, f"after dropping {sorted(drop)}:")

    orphan_pairs = base_pairs - kept_pairs           # lost ALL their labels
    lost_queries = base_q - kept_q                   # query has no labels left at all
    print(f"\n  -> orphaned pairs (need a fresh label) : {len(orphan_pairs)}")
    print(f"  -> queries that lose ALL coverage       : {len(lost_queries)}  {sorted(lost_queries) if lost_queries else ''}")

    # how concentrated is the gap? orphaned pairs per query
    per_q = defaultdict(int)
    for (q, _c) in orphan_pairs:
        per_q[q] += 1
    if per_q:
        worst = sorted(per_q.items(), key=lambda x: -x[1])[:8]
        print(f"  -> orphaned pairs span {len(per_q)} queries; worst: {worst}")
        print(f"  -> if a student re-grades the {len(orphan_pairs)} orphaned pairs, full coverage is restored.")


if __name__ == "__main__":
    main()
