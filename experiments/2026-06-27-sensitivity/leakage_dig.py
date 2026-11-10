"""Investigate the H1 held-out reversal: is the hybrid advantage on synthetic
queries a lexical-overlap (test-construction) artifact, or a real effect?

Four checks (reuses the cached retrieval runs from sensitivity.py):
  1. all four retrievers' nDCG@5 / Recall@5 split by source (synth vs held-out
     BAC-2025). If BM25-only is strong on synth but collapses on BAC while dense
     is flat, the hybrid gain on synth is the keyword channel exploiting overlap.
  2. the 9 held-out BAC queries one by one (dense vs hybrid nDCG@5) — is the
     reversal broad or one or two flukes?
  3. a bootstrap CI on the BAC-9 H1 nDCG@5 delta — is it distinguishable from 0?
  4. direct lexical overlap: for each query, the fraction of its (French-
     tokenised) terms that appear in its relevant chunks, averaged by slice.
     Higher overlap on synth would be the mechanism, measured directly.

Run:
  uv run python experiments/2026-06-27-sensitivity/leakage_dig.py \
      --labels "experiments/annotated/T*.jsonl"
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.qrels import load_labels  # noqa: E402
from src.eval.relevance.retrieval_metrics import ndcg_at_k, recall_at_k  # noqa: E402
from src.retrieval.tokenizer_fr import FrenchTokenizer  # noqa: E402

HERE = Path(__file__).resolve().parent
VARIANTS = ("bm25", "dense", "hybrid", "instructional")
K = 5
SEED = 42
logger = logging.getLogger("leakage")


def is_bac(qid: str) -> bool:
    return qid.startswith("bac2025")


def build_qrels(labels):
    by_pair = defaultdict(list)
    for la in labels:
        by_pair[(la["query_id"], la["chunk_id"])].append(la["relevance"])
    qrels = defaultdict(dict)
    for (qid, cid), rels in by_pair.items():
        qrels[qid][cid] = int(sum(rels) / len(rels) + 0.5)
    return dict(qrels)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("--runs-cache", type=Path, default=HERE / "runs.json")
    ap.add_argument("--pairs", type=Path, default=REPO_ROOT / "results/relevance_pairs.jsonl")
    ap.add_argument("--out", type=Path, default=HERE / "leakage_dig.json")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if not args.runs_cache.exists():
        raise SystemExit("runs.json not found — run sensitivity.py first to build the runs cache.")
    runs = json.loads(args.runs_cache.read_text(encoding="utf-8"))
    labels = load_labels([Path(p) for p in glob.glob(args.labels)])
    qrels = build_qrels(labels)
    relevant = {q: {c for c, r in ch.items() if r >= 2} for q, ch in qrels.items()}

    # query + chunk text from the pairs file (for lexical overlap)
    qtext: dict[str, str] = {}
    chunktext: dict[str, str] = {}
    for line in args.pairs.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            qtext[r["query_id"]] = r.get("query_text", "")
            chunktext[r["chunk_id"]] = r.get("chunk_text", "")

    qids = sorted(qrels)
    syn = [q for q in qids if not is_bac(q)]
    bac = [q for q in qids if is_bac(q)]

    # ---- per-query metrics for all variants ----
    def ndcg(q, v):
        return ndcg_at_k(runs[v].get(q, []), qrels[q], K)

    def rec(q, v):
        return recall_at_k(runs[v].get(q, []), relevant.get(q, set()), K)

    def nanmean(xs):
        xs = [x for x in xs if x == x]
        return sum(xs) / len(xs) if xs else float("nan")

    # ---- check 1: all variants per slice ----
    slices = {"synth": syn, "bac2025_heldout": bac, "all": qids}
    by_slice = {}
    for name, qs in slices.items():
        by_slice[name] = {
            "n": len(qs),
            **{f"{v}_ndcg@5": round(nanmean([ndcg(q, v) for q in qs]), 4) for v in VARIANTS},
            **{f"{v}_recall@5": round(nanmean([rec(q, v) for q in qs]), 4) for v in VARIANTS},
        }

    # ---- check 2: the 9 BAC queries one by one ----
    bac_detail = [
        {
            "query_id": q,
            "dense_ndcg@5": round(ndcg(q, "dense"), 3),
            "hybrid_ndcg@5": round(ndcg(q, "hybrid"), 3),
            "delta": round(ndcg(q, "hybrid") - ndcg(q, "dense"), 3),
            "n_relevant": len(relevant.get(q, set())),
            "query": qtext.get(q, "")[:80],
        }
        for q in bac
    ]
    bac_detail.sort(key=lambda d: d["delta"])

    # ---- check 3: bootstrap CI on BAC-9 H1 nDCG@5 ----
    rng = random.Random(SEED)
    dh = [(ndcg(q, "hybrid"), ndcg(q, "dense")) for q in bac]
    deltas = []
    for _ in range(2000):
        sample = [rng.choice(dh) for _ in dh]
        deltas.append(nanmean([h for h, _ in sample]) - nanmean([d for _, d in sample]))
    deltas.sort()
    bac_boot = {
        "mean": round(sum(deltas) / len(deltas), 4),
        "ci95": [round(deltas[int(0.025 * len(deltas))], 4),
                 round(deltas[int(0.975 * len(deltas))], 4)],
        "frac_negative": round(sum(1 for d in deltas if d < 0) / len(deltas), 3),
    }

    # ---- check 4: lexical overlap of query terms with its relevant chunks ----
    tok = FrenchTokenizer()

    def overlap(q):
        qt = set(tok.tokenize(qtext.get(q, "")))
        if not qt:
            return float("nan")
        rel_terms: set[str] = set()
        for cid in relevant.get(q, set()):
            rel_terms |= set(tok.tokenize(chunktext.get(cid, "")))
        if not relevant.get(q, set()):
            return float("nan")
        return len(qt & rel_terms) / len(qt)

    lex = {
        "synth_mean_query_term_coverage": round(nanmean([overlap(q) for q in syn]), 4),
        "bac_mean_query_term_coverage": round(nanmean([overlap(q) for q in bac]), 4),
    }

    report = {"by_slice": by_slice, "bac_query_detail": bac_detail,
              "bac9_h1_bootstrap": bac_boot, "lexical_overlap": lex}
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Check 1: all retrievers' nDCG@5 / Recall@5 by slice ===")
    print(f"  {'slice':<18}{'n':>4}" + "".join(f"{v[:6]:>9}" for v in VARIANTS))
    for name, d in by_slice.items():
        print(f"  {name:<18}{d['n']:>4}" + "".join(f"{d[f'{v}_ndcg@5']:>9.3f}" for v in VARIANTS)
              + "   (nDCG@5)")
        print(f"  {'':<18}{'':>4}" + "".join(f"{d[f'{v}_recall@5']:>9.3f}" for v in VARIANTS)
              + "   (Recall@5)")

    print("\n=== Check 2: the 9 held-out BAC queries (hybrid - dense nDCG@5) ===")
    for d in bac_detail:
        print(f"  {d['query_id']:<16} dense {d['dense_ndcg@5']:.2f}  hybrid {d['hybrid_ndcg@5']:.2f}"
              f"  delta {d['delta']:+.2f}  (rel={d['n_relevant']})  {d['query']}")

    print("\n=== Check 3: bootstrap on BAC-9 H1 nDCG@5 ===")
    print(f"  mean {bac_boot['mean']:+.3f}  95% CI [{bac_boot['ci95'][0]:+.3f}, "
          f"{bac_boot['ci95'][1]:+.3f}]  P(<0)={bac_boot['frac_negative']:.2f}")

    print("\n=== Check 4: query-term coverage by relevant chunks (lexical overlap) ===")
    print(f"  synth: {lex['synth_mean_query_term_coverage']:.3f}   "
          f"bac:   {lex['bac_mean_query_term_coverage']:.3f}")
    print(f"\nreport -> {args.out}")


if __name__ == "__main__":
    main()
