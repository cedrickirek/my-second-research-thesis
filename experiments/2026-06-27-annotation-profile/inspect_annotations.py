"""Annotation quality-control: surface anomalies that may be annotator error.

Run BEFORE accepting the H1/H2/agreement numbers. The point is to decide whether
any labels need a second look (or re-annotation), not to compute metrics. It
surfaces, with full context for manual inspection:

  1. rater profile + heuristic flags — severity outliers and distribution-shape
     oddities (concentrated on one grade, never uses the top/bottom grade,
     U-shaped/near-binary) that can signal a misread rubric or low effort.
  2. anchor disagreements — every doubly-rated pair whose two grades differ by
     >= 2, with the query text + chunk context, so a human can judge who (if
     anyone) is wrong. A 0-vs-3 split is the strongest re-annotation candidate.
  3. rater involvement in those disagreements — a rater appearing in many is a
     re-annotation candidate.
  4. top-rank-non-relevant — hybrid rank-1 chunks graded 0 (retrieval miss vs
     label error).
  5. annotator notes — any free-text the annotators left.

Heuristic flags are attention-directors, not verdicts.

Run:
  uv run python experiments/2026-06-27-annotation-profile/inspect_annotations.py \
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
SPREAD_FLAG = 2  # |grade difference| >= this on a shared pair -> inspect
logger = logging.getLogger("annotation_qc")


def load_pair_context(path: Path) -> dict[str, dict]:
    """pair_id -> context for manual inspection (text truncated)."""
    ctx: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        chunk_text = (r.get("chunk_text") or "").replace("\n", " ")
        ctx[r["pair_id"]] = {
            "query_text": r.get("query_text"),
            "content_type": r.get("chunk_content_type"),
            "heading": r.get("chunk_heading"),
            "topic": r.get("chunk_topic"),
            "rank_hybrid": r.get("rank_hybrid"),
            "retrieved_by": r.get("retrieved_by") or [],
            "chunk_preview": chunk_text[:240],
        }
    return ctx


def rater_profile(labels: list[dict], overall_mean: float) -> dict:
    by_rater: dict[str, list[int]] = defaultdict(list)
    for la in labels:
        by_rater[la["annotator"]].append(la["relevance"])
    out: dict[str, dict] = {}
    for rid, gs in sorted(by_rater.items()):
        n = len(gs)
        c = Counter(gs)
        mean = sum(gs) / n
        pct = {g: c.get(g, 0) / n for g in GRADES}
        modal_grade, modal_count = c.most_common(1)[0]
        flags = []
        if mean >= overall_mean + 0.4:
            flags.append("lenient")
        if mean <= overall_mean - 0.3:
            flags.append("severe")
        if pct[3] < 0.02:
            flags.append("never_top(3)")
        if pct[0] < 0.10:
            flags.append("never_zero(0)")
        if modal_count / n > 0.60:
            flags.append(f"concentrated@{modal_grade}({modal_count / n:.0%})")
        if pct[0] + pct[3] > 0.60 and pct[1] + pct[2] < 0.40:
            flags.append("U-shaped/near-binary")
        out[rid] = {
            "n": n,
            "mean": round(mean, 3),
            "pct_relevant": round(sum(1 for g in gs if g >= 2) / n, 3),
            "pct": {str(g): round(pct[g], 3) for g in GRADES},
            "modal_grade": modal_grade,
            "flags": flags,
        }
    return out


def anchor_disagreements(labels: list[dict], ctx: dict[str, dict]) -> dict:
    grades_by_pair: dict[str, dict[str, int]] = defaultdict(dict)
    for la in labels:
        grades_by_pair[la["pair_id"]][la["annotator"]] = la["relevance"]
    anchor = {p: g for p, g in grades_by_pair.items() if len(g) >= 2}
    raters_per_pair = Counter(len(g) for g in anchor.values())
    spread_hist: Counter[int] = Counter()
    disagreements = []
    involvement: Counter[str] = Counter()
    for pid, g in anchor.items():
        vals = list(g.values())
        spread = max(vals) - min(vals)
        spread_hist[spread] += 1
        if spread >= SPREAD_FLAG:
            qid = pid.split("__", 1)[0]
            c = ctx.get(pid, {})
            disagreements.append(
                {
                    "pair_id": pid,
                    "spread": spread,
                    "grades": g,
                    "query_id": qid,
                    "query_text": c.get("query_text"),
                    "content_type": c.get("content_type"),
                    "heading": c.get("heading"),
                    "topic": c.get("topic"),
                    "rank_hybrid": c.get("rank_hybrid"),
                    "retrieved_by": c.get("retrieved_by"),
                    "chunk_preview": c.get("chunk_preview"),
                }
            )
            for rid in g:
                involvement[rid] += 1
    disagreements.sort(key=lambda d: (-d["spread"], d["pair_id"]))
    return {
        "n_anchor_pairs": len(anchor),
        "raters_per_anchor_pair": dict(raters_per_pair),
        "spread_hist": {str(s): spread_hist.get(s, 0) for s in range(4)},
        "n_flagged": len(disagreements),
        "rater_involvement": dict(involvement.most_common()),
        "disagreements": disagreements,
    }


def top_rank_nonrelevant(labels: list[dict], ctx: dict[str, dict]) -> dict:
    """Pairs the hybrid retriever ranked #1 but that got graded 0 (mean)."""
    grades_by_pair: dict[str, list[int]] = defaultdict(list)
    for la in labels:
        grades_by_pair[la["pair_id"]].append(la["relevance"])
    hits = []
    for pid, gs in grades_by_pair.items():
        c = ctx.get(pid, {})
        if c.get("rank_hybrid") == 1:
            mean = sum(gs) / len(gs)
            if mean < 1.0:
                hits.append(
                    {
                        "pair_id": pid,
                        "mean_grade": round(mean, 2),
                        "grades": gs,
                        "query_text": c.get("query_text"),
                        "content_type": c.get("content_type"),
                        "heading": c.get("heading"),
                        "chunk_preview": c.get("chunk_preview"),
                    }
                )
    hits.sort(key=lambda h: h["mean_grade"])
    return {"n": len(hits), "items": hits}


def notes_dump(labels: list[dict]) -> list[dict]:
    return [
        {"pair_id": la["pair_id"], "annotator": la["annotator"],
         "relevance": la["relevance"], "notes": la["notes"]}
        for la in labels
        if (la.get("notes") or "").strip()
    ]


def print_report(rp: dict, anc: dict, trn: dict, notes: list[dict]) -> None:
    print("\n=== Rater profile + flags ===")
    for rid, d in rp.items():
        p = d["pct"]
        print(f"  {rid:<5} n={d['n']:>4} mean={d['mean']:.2f} %rel={d['pct_relevant']*100:4.1f}"
              f"  [0:{p['0']*100:4.1f} 1:{p['1']*100:4.1f} 2:{p['2']*100:4.1f} 3:{p['3']*100:4.1f}]"
              f"  {' '.join(d['flags']) if d['flags'] else '-'}")

    print("\n=== Anchor agreement ===")
    print(f"  anchor pairs={anc['n_anchor_pairs']}  raters/pair={anc['raters_per_anchor_pair']}")
    print(f"  spread histogram (|max-min|): {anc['spread_hist']}")
    print(f"  flagged (spread>={SPREAD_FLAG}): {anc['n_flagged']}")
    print(f"  rater involvement in flagged: {anc['rater_involvement']}")

    print(f"\n=== Disagreement pairs to inspect (spread>={SPREAD_FLAG}) ===")
    for d in anc["disagreements"]:
        gr = " ".join(f"{r}:{v}" for r, v in d["grades"].items())
        print(f"\n  [{d['pair_id']}] spread={d['spread']}  grades: {gr}")
        print(f"    Q: {d['query_text']}")
        print(f"    chunk: {d['content_type']} / {d['heading']} / {d['topic']} "
              f"(hybrid rank {d['rank_hybrid']}, by {d['retrieved_by']})")
        print(f"    >> {d['chunk_preview']}")

    print(f"\n=== Hybrid rank-1 chunks graded ~non-relevant ({trn['n']}) ===")
    for h in trn["items"]:
        print(f"  [{h['pair_id']}] mean={h['mean_grade']} grades={h['grades']} "
              f"{h['content_type']}/{h['heading']}")
        print(f"    Q: {h['query_text']}")

    print(f"\n=== Annotator notes ({len(notes)}) ===")
    for nt in notes:
        print(f"  {nt['annotator']} [{nt['pair_id']}] rel={nt['relevance']}: {nt['notes']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True, help="glob of label files (.jsonl/.csv)")
    ap.add_argument(
        "--pairs", type=Path, default=REPO_ROOT / "results/relevance_pairs.jsonl"
    )
    ap.add_argument("--out", type=Path, default=HERE / "annotation_qc.json")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # Math symbols (√, etc.) in queries break the default Windows cp1252 console.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    paths = [Path(p) for p in glob.glob(args.labels)]
    if not paths:
        raise SystemExit(f"no label files match {args.labels!r}")
    labels = load_labels(paths)
    ctx = load_pair_context(args.pairs)
    overall_mean = sum(la["relevance"] for la in labels) / len(labels)
    logger.info("loaded %d labels; overall mean grade %.3f", len(labels), overall_mean)

    rp = rater_profile(labels, overall_mean)
    anc = anchor_disagreements(labels, ctx)
    trn = top_rank_nonrelevant(labels, ctx)
    notes = notes_dump(labels)

    args.out.write_text(
        json.dumps(
            {"overall_mean": overall_mean, "rater_profile": rp,
             "anchor": anc, "top_rank_nonrelevant": trn, "notes": notes},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print_report(rp, anc, trn, notes)
    print(f"\nqc -> {args.out}")


if __name__ == "__main__":
    main()
