"""Descriptive profile of the returned relevance annotations (dataset properties).

This is *not* a hypothesis test. It joins the returned labels (pair_id ->
relevance, annotator) onto the dispatched pair metadata (content_type,
retrieved_by, question_type, bucket) and reports the marginal structure of the
annotations, to (a) document the dataset and (b) help interpret the agreement
and H2 results produced by `experiments/2026-06-20-dispatch-analysis/analyze.py`.

Cuts (each earns a place by explaining a headline number):
  1. overall  — the 0-3 relevance base-rate (prevalence -> nominal-alpha deflation).
  2. annotator — per-rater severity. Reported BOTH over each rater's own items and
                 restricted to the shared anchor (multi-rated pairs), because the
                 anchor controls item difficulty; the cross-item version conflates
                 severity with which pairs each rater happened to receive.
  3. content_type — relevance by chunk content_type. The H2 instrument check: if
                    example/solution chunks score lower than theory on per-chunk
                    relevance, that under-credits instructional retrieval.
  4. retriever — relevance by `retrieved_by`. Pool-precision per method. Pools
                 OVERLAP (a pair can be surfaced by several retrievers), so this is
                 "share of what this method surfaced that was judged relevant",
                 not an exclusive partition.
  5. per_query — relevant-chunk count per query (threshold >= 2). qrels-health:
                 how many queries have zero relevant chunks (recall undefined).
  6. question_type / bucket — secondary, emitted to JSON, not foregrounded.

Run:
  uv run python experiments/2026-06-27-annotation-profile/describe_annotations.py \
      --labels "experiments/annotated/T*.jsonl"
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.qrels import load_labels  # noqa: E402

HERE = Path(__file__).resolve().parent
GRADES = (0, 1, 2, 3)
RELEVANT_THRESHOLD = 2

logger = logging.getLogger("annotation_profile")


def load_pair_meta(path: Path) -> dict[str, dict]:
    """pair_id -> the dispatched metadata we slice relevance by."""
    meta: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        meta[r["pair_id"]] = {
            "content_type": r.get("chunk_content_type"),
            "retrieved_by": r.get("retrieved_by") or [],
            "question_type": r.get("query_question_type"),
            "bucket": r.get("query_bucket"),
            "topic": r.get("chunk_topic"),
        }
    return meta


def _dist(grades: list[int]) -> dict:
    """Count, percentage by grade, mean, and %relevant for a list of grades."""
    n = len(grades)
    counts = Counter(grades)
    return {
        "n": n,
        "counts": {str(g): counts.get(g, 0) for g in GRADES},
        "pct": {str(g): (counts.get(g, 0) / n if n else 0.0) for g in GRADES},
        "mean": (sum(grades) / n if n else 0.0),
        "pct_relevant": (
            sum(1 for g in grades if g >= RELEVANT_THRESHOLD) / n if n else 0.0
        ),
    }


def profile(labels: list[dict], meta: dict[str, dict]) -> dict:
    missing_meta = sum(1 for la in labels if la["pair_id"] not in meta)
    if missing_meta:
        logger.warning("%d labels have no pair metadata (skipped in slices)", missing_meta)

    # ---- 1. overall ----
    all_grades = [la["relevance"] for la in labels]
    overall = _dist(all_grades)

    # ---- 2. per-annotator (own items + anchor-restricted) ----
    by_rater: dict[str, list[int]] = defaultdict(list)
    raters_per_pair: dict[str, set[str]] = defaultdict(set)
    for la in labels:
        by_rater[la["annotator"]].append(la["relevance"])
        raters_per_pair[la["pair_id"]].add(la["annotator"])
    anchor = {pid for pid, rs in raters_per_pair.items() if len(rs) >= 2}
    by_rater_anchor: dict[str, list[int]] = defaultdict(list)
    for la in labels:
        if la["pair_id"] in anchor:
            by_rater_anchor[la["annotator"]].append(la["relevance"])
    annotator = {
        rid: {
            "all_items": _dist(grades),
            "anchor_only": _dist(by_rater_anchor.get(rid, [])),
        }
        for rid, grades in sorted(by_rater.items())
    }

    # ---- 3. content_type ----
    by_ctype: dict[str, list[int]] = defaultdict(list)
    for la in labels:
        m = meta.get(la["pair_id"])
        if m and m["content_type"]:
            by_ctype[m["content_type"]].append(la["relevance"])
    content_type = {ct: _dist(g) for ct, g in sorted(by_ctype.items())}

    # ---- 4. retriever (overlapping pools) ----
    by_retriever: dict[str, list[int]] = defaultdict(list)
    for la in labels:
        m = meta.get(la["pair_id"])
        if not m:
            continue
        for rv in m["retrieved_by"]:
            by_retriever[rv].append(la["relevance"])
    retriever = {rv: _dist(g) for rv, g in sorted(by_retriever.items())}

    # ---- 5. per-query relevant density (graded by round-half-up of mean) ----
    grades_by_pair: dict[str, list[int]] = defaultdict(list)
    qid_of_pair: dict[str, str] = {}
    for la in labels:
        grades_by_pair[la["pair_id"]].append(la["relevance"])
        qid_of_pair[la["pair_id"]] = la["query_id"]
    rel_per_query: dict[str, int] = defaultdict(int)
    judged_per_query: dict[str, int] = defaultdict(int)
    for pid, gs in grades_by_pair.items():
        qid = qid_of_pair[pid]
        judged_per_query[qid] += 1
        graded = int(sum(gs) / len(gs) + 0.5)  # round-half-up, matches qrels.py
        if graded >= RELEVANT_THRESHOLD:
            rel_per_query[qid] += 1
    counts = sorted(rel_per_query.get(q, 0) for q in judged_per_query)
    n_q = len(judged_per_query)
    per_query = {
        "n_queries": n_q,
        "queries_with_zero_relevant": sum(1 for c in counts if c == 0),
        "min": counts[0] if counts else 0,
        "median": counts[n_q // 2] if counts else 0,
        "max": counts[-1] if counts else 0,
        "mean_relevant_per_query": (sum(counts) / n_q if n_q else 0.0),
        "mean_judged_per_query": (
            sum(judged_per_query.values()) / n_q if n_q else 0.0
        ),
    }

    # ---- 6. secondary: question_type, bucket ----
    def _by(key: str) -> dict:
        buckets: dict[str, list[int]] = defaultdict(list)
        for la in labels:
            m = meta.get(la["pair_id"])
            if m and m.get(key):
                buckets[m[key]].append(la["relevance"])
        return {k: _dist(g) for k, g in sorted(buckets.items())}

    return {
        "n_labels": len(labels),
        "n_pairs_labeled": len(grades_by_pair),
        "n_anchor_pairs": len(anchor),
        "n_raters": len(by_rater),
        "missing_meta": missing_meta,
        "overall": overall,
        "annotator": annotator,
        "content_type": content_type,
        "retriever": retriever,
        "per_query": per_query,
        "question_type": _by("question_type"),
        "bucket": _by("bucket"),
    }


def _fmt_dist(d: dict) -> str:
    p = d["pct"]
    return (
        f"n={d['n']:>4}  mean={d['mean']:.2f}  "
        f"%rel={d['pct_relevant']*100:4.1f}  "
        f"[0:{p['0']*100:4.1f} 1:{p['1']*100:4.1f} "
        f"2:{p['2']*100:4.1f} 3:{p['3']*100:4.1f}]"
    )


def print_report(p: dict) -> None:
    print("\n=== Annotation profile ===")
    print(
        f"labels={p['n_labels']}  pairs={p['n_pairs_labeled']}  "
        f"anchor={p['n_anchor_pairs']}  raters={p['n_raters']}"
    )
    print("\n[overall]              " + _fmt_dist(p["overall"]))

    print("\n[per annotator]  (all items | anchor-only)")
    for rid, d in p["annotator"].items():
        print(f"  {rid:<5} all    {_fmt_dist(d['all_items'])}")
        print(f"  {'':<5} anchor {_fmt_dist(d['anchor_only'])}")

    print("\n[by chunk content_type]")
    for ct, d in p["content_type"].items():
        print(f"  {ct:<12} {_fmt_dist(d)}")

    print("\n[by retriever  (overlapping pools = pool precision)]")
    for rv, d in p["retriever"].items():
        print(f"  {rv:<14} {_fmt_dist(d)}")

    print("\n[per-query relevant density  (graded relevance >= 2)]")
    pq = p["per_query"]
    print(
        f"  queries={pq['n_queries']}  zero-relevant={pq['queries_with_zero_relevant']}"
        f"  min/median/max={pq['min']}/{pq['median']}/{pq['max']}"
        f"  mean_rel/q={pq['mean_relevant_per_query']:.2f}"
        f"  mean_judged/q={pq['mean_judged_per_query']:.1f}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True, help="glob of label files (.jsonl/.csv)")
    ap.add_argument(
        "--pairs", type=Path, default=REPO_ROOT / "results/relevance_pairs.jsonl"
    )
    ap.add_argument("--out", type=Path, default=HERE / "annotation_profile.json")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    paths = [Path(p) for p in glob.glob(args.labels)]
    if not paths:
        raise SystemExit(f"no label files match {args.labels!r}")
    labels = load_labels(paths)
    logger.info("loaded %d labels from %d file(s)", len(labels), len(paths))
    meta = load_pair_meta(args.pairs)
    logger.info("loaded metadata for %d pairs", len(meta))

    p = profile(labels, meta)
    args.out.write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")
    print_report(p)
    print(f"\nprofile -> {args.out}")


if __name__ == "__main__":
    main()