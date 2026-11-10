"""Sensitivity / robustness analysis of H1 and H2 to annotator behaviour.

Rather than reporting H1/H2 from a single qrels, we rebuild the qrels under a
menu of plausible annotator-behaviour scenarios and recompute the verdicts. If
the direction holds across scenarios, the claim is robust to the rater
heterogeneity documented in the QC; if it flips, we report exactly where.

Scenarios (each -> qrels -> H1, H2, alpha):
  * threshold@{1,2,3}    — relevance cut for "relevant" (baseline = 2).
  * leave-one-annotator  — drop each rater in turn (does one rater drive it?).
  * recalibrated         — remove per-rater severity: g' = round(g - mean_r +
                           mean_all), clipped 0-3 (mean-centred to the panel).
  * optimistic / pessimistic — resolve every multi-rated pair by max / min
                           instead of round-half-up mean (anchor-disagreement
                           envelope).

Plus a PAIRED QUERY-LEVEL BOOTSTRAP on the baseline qrels: resample the judged
queries with replacement to get a CI on the H1/H2 deltas and the fraction of
resamples in which the verdict holds (the significance the report otherwise
lacks; master task 28).

H1 = hybrid - dense at k=10 (both return 10 -> fair).
H2 = instructional - hybrid at k=5 (instructional caps at 5 -> matched cutoff).

Retrieval runs do NOT depend on labels, so they are computed once and cached to
runs.json; only scoring is re-done per scenario.

Run:
  uv run python experiments/2026-06-27-sensitivity/sensitivity.py \
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

from src.eval.relevance.agreement import summarize  # noqa: E402
from src.eval.relevance.qrels import agreement_records, load_labels  # noqa: E402
from src.eval.relevance.retrieval_metrics import (  # noqa: E402
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)

HERE = Path(__file__).resolve().parent
CANDIDATES = 20
VARIANTS = ("bm25", "dense", "hybrid", "instructional")
H1_K, H2_K = 10, 5
N_BOOTSTRAP = 2000
SEED = 42
logger = logging.getLogger("sensitivity")


# --------------------------------------------------------------------------- #
# qrels builders (mean / max / min aggregation; round-half-up for mean)
# --------------------------------------------------------------------------- #
def _round_half_up(x: float) -> int:
    return int(x + 0.5)


def qrels_from_labels(labels: list[dict], agg: str = "mean") -> dict[str, dict[str, int]]:
    by_pair: dict[tuple[str, str], list[int]] = defaultdict(list)
    for la in labels:
        by_pair[(la["query_id"], la["chunk_id"])].append(la["relevance"])
    out: dict[str, dict[str, int]] = defaultdict(dict)
    for (qid, cid), rels in by_pair.items():
        if agg == "mean":
            out[qid][cid] = _round_half_up(sum(rels) / len(rels))
        elif agg == "max":
            out[qid][cid] = max(rels)
        elif agg == "min":
            out[qid][cid] = min(rels)
        else:
            raise ValueError(agg)
    return dict(out)


def relevant_sets(qrels: dict[str, dict[str, int]], threshold: int) -> dict[str, set[str]]:
    return {
        qid: {cid for cid, rel in chunks.items() if rel >= threshold}
        for qid, chunks in qrels.items()
    }


def recalibrate(labels: list[dict]) -> list[dict]:
    """Mean-centre each rater to the panel mean, then re-discretise to 0-3."""
    by_rater: dict[str, list[int]] = defaultdict(list)
    for la in labels:
        by_rater[la["annotator"]].append(la["relevance"])
    rater_mean = {r: sum(v) / len(v) for r, v in by_rater.items()}
    grand = sum(la["relevance"] for la in labels) / len(labels)
    out = []
    for la in labels:
        adj = _round_half_up(la["relevance"] - rater_mean[la["annotator"]] + grand)
        out.append({**la, "relevance": max(0, min(3, adj))})
    return out


# --------------------------------------------------------------------------- #
# scoring
# --------------------------------------------------------------------------- #
def per_query_metrics(
    run: dict[str, list[str]],
    qrels: dict[str, dict[str, int]],
    relevant: dict[str, set[str]],
) -> dict[str, dict[str, float]]:
    """qid -> {metric: value or nan} for the queries present in run & qrels."""
    out: dict[str, dict[str, float]] = {}
    for qid in run:
        if qid not in qrels:
            continue
        rel = relevant.get(qid, set())
        out[qid] = {
            f"recall@{H1_K}": recall_at_k(run[qid], rel, H1_K),
            f"ndcg@{H1_K}": ndcg_at_k(run[qid], qrels[qid], H1_K),
            f"recall@{H2_K}": recall_at_k(run[qid], rel, H2_K),
            f"ndcg@{H2_K}": ndcg_at_k(run[qid], qrels[qid], H2_K),
            "mrr": reciprocal_rank(run[qid], rel),
        }
    return out


def _nanmean(xs: list[float]) -> float:
    vals = [x for x in xs if x == x]  # drop nan
    return sum(vals) / len(vals) if vals else float("nan")


def mean_metrics(pq: dict[str, dict[str, float]], qids: list[str]) -> dict[str, float]:
    keys = next(iter(pq.values())).keys() if pq else []
    return {k: _nanmean([pq[q][k] for q in qids if q in pq]) for k in keys}


def hypotheses(runs, qrels, threshold):
    rel = relevant_sets(qrels, threshold)
    pq = {v: per_query_metrics(runs[v], qrels, rel) for v in VARIANTS}
    qids = sorted(qrels)
    m = {v: mean_metrics(pq[v], qids) for v in VARIANTS}
    n_rel = sum(len(s) for s in rel.values())
    return {
        "n_queries": len(qids),
        "n_relevant_pairs": n_rel,
        f"H1_recall@{H1_K}": m["hybrid"][f"recall@{H1_K}"] - m["dense"][f"recall@{H1_K}"],
        f"H1_ndcg@{H1_K}": m["hybrid"][f"ndcg@{H1_K}"] - m["dense"][f"ndcg@{H1_K}"],
        f"H2_recall@{H2_K}": m["instructional"][f"recall@{H2_K}"] - m["hybrid"][f"recall@{H2_K}"],
        f"H2_ndcg@{H2_K}": m["instructional"][f"ndcg@{H2_K}"] - m["hybrid"][f"ndcg@{H2_K}"],
    }, pq


def alpha_ordinal(labels: list[dict]) -> float:
    return summarize(agreement_records(labels)).get("krippendorff_alpha_ordinal", float("nan"))


def stratified(runs, qrels, threshold, query_bucket) -> dict:
    """nDCG@5 split by source (synth vs held-out BAC-2025) and by query bucket.

    The BAC-2025 split is the leakage control: BAC 2025 is de-indexed, so an H1
    advantage surviving on that slice cannot be a train/test-overlap artifact.
    """
    rel = relevant_sets(qrels, threshold)
    pq = {v: per_query_metrics(runs[v], qrels, rel) for v in VARIANTS}
    nk = f"ndcg@{H2_K}"

    def grp(qids: list[str], label: str) -> dict:
        m = {v: mean_metrics(pq[v], qids) for v in VARIANTS}
        return {
            "group": label,
            "n": len(qids),
            "dense_ndcg@5": round(m["dense"][nk], 4),
            "hybrid_ndcg@5": round(m["hybrid"][nk], 4),
            "ped_ndcg@5": round(m["instructional"][nk], 4),
            "H1_ndcg@5": round(m["hybrid"][nk] - m["dense"][nk], 4),
            "H2_ndcg@5": round(m["instructional"][nk] - m["hybrid"][nk], 4),
        }

    qids = sorted(qrels)
    bac = [q for q in qids if q.startswith("bac2025")]
    syn = [q for q in qids if not q.startswith("bac2025")]
    by_bucket = defaultdict(list)
    for q in qids:
        by_bucket[query_bucket.get(q, "unknown")].append(q)
    return {
        "by_source": [grp(syn, "synth"), grp(bac, "bac2025_heldout")],
        "by_bucket": [grp(qs, bk) for bk, qs in sorted(by_bucket.items())],
    }


# --------------------------------------------------------------------------- #
# retrieval runs (computed once, cached)
# --------------------------------------------------------------------------- #
def compute_runs(qtext: dict[str, str]) -> dict[str, dict[str, list[str]]]:
    from src.retrieval.bm25_index import BM25Index
    from src.retrieval.corpus_loader import load_chunks
    from src.retrieval.dense_index import DEFAULT_MODEL, DenseIndex, default_cache_path
    from src.retrieval.hybrid import HybridRetriever
    from src.retrieval.instructional import InstructionalRetriever
    from src.retrieval.tokenizer_fr import FrenchTokenizer

    chunks = load_chunks(REPO_ROOT / "data/corpus/chunks.jsonl")
    bm25 = BM25Index(chunks, FrenchTokenizer())
    dense = DenseIndex(chunks, model_name=DEFAULT_MODEL,
                       embeddings_cache=default_cache_path(DEFAULT_MODEL))
    hybrid = HybridRetriever(bm25, dense, rrf_k=60)
    instructional = InstructionalRetriever(hybrid, chunks)
    runs = {v: {} for v in VARIANTS}
    for qid, text in qtext.items():
        runs["bm25"][qid] = [h.chunk_id for h in bm25.search(text, k=H1_K)]
        runs["dense"][qid] = [h.chunk_id for h in dense.search(text, k=H1_K)]
        runs["hybrid"][qid] = [
            h.chunk_id
            for h in hybrid.search(text, k=H1_K, candidates_per_retriever=CANDIDATES)
        ]
        runs["instructional"][qid] = [
            c.metadata.chunk_id
            for c in instructional.search(text, candidates_per_retriever=CANDIDATES).selected
        ]
    return runs


def load_or_build_runs(qtext, cache: Path, refresh: bool) -> dict:
    if cache.exists() and not refresh:
        logger.info("loading cached runs from %s", cache.name)
        return json.loads(cache.read_text(encoding="utf-8"))
    logger.info("computing retrieval runs (loads e5-large once)...")
    runs = compute_runs(qtext)
    cache.write_text(json.dumps(runs, ensure_ascii=False), encoding="utf-8")
    return runs


# --------------------------------------------------------------------------- #
# bootstrap
# --------------------------------------------------------------------------- #
def bootstrap(pq_by_variant, qids, b=N_BOOTSTRAP, seed=SEED) -> dict:
    rng = random.Random(seed)
    # H1 at both cut-offs (primary is nDCG@5); H2 only at the matched k=5.
    keys_h1 = [f"recall@{H2_K}", f"ndcg@{H2_K}", f"recall@{H1_K}", f"ndcg@{H1_K}", "mrr"]
    keys_h2 = [f"recall@{H2_K}", f"ndcg@{H2_K}", "mrr"]
    samples = {f"H1_{k}": [] for k in keys_h1}
    samples.update({f"H2_{k}": [] for k in keys_h2})
    for _ in range(b):
        res = [rng.choice(qids) for _ in qids]
        m = {v: mean_metrics(pq_by_variant[v], res) for v in VARIANTS}
        for k in keys_h1:
            samples[f"H1_{k}"].append(m["hybrid"][k] - m["dense"][k])
        for k in keys_h2:
            samples[f"H2_{k}"].append(m["instructional"][k] - m["hybrid"][k])

    def ci(xs):
        xs = sorted(x for x in xs if x == x)
        lo = xs[int(0.025 * len(xs))]
        hi = xs[int(0.975 * len(xs))]
        mean = sum(xs) / len(xs)
        frac_pos = sum(1 for x in xs if x > 0) / len(xs)
        return {"mean": round(mean, 4), "ci95": [round(lo, 4), round(hi, 4)],
                "frac_positive": round(frac_pos, 4)}

    return {k: ci(v) for k, v in samples.items()}


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("--queries", type=Path, default=REPO_ROOT / "data/eval/queries.jsonl")
    ap.add_argument("--pairs", type=Path, default=REPO_ROOT / "results/relevance_pairs.jsonl")
    ap.add_argument("--out", type=Path, default=HERE / "sensitivity.json")
    ap.add_argument("--runs-cache", type=Path, default=HERE / "runs.json")
    ap.add_argument("--refresh-runs", action="store_true")
    ap.add_argument("--bootstrap", type=int, default=N_BOOTSTRAP)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    paths = [Path(p) for p in glob.glob(args.labels)]
    labels = load_labels(paths)
    base_qrels = qrels_from_labels(labels, "mean")
    qtext = {}
    for line in args.queries.read_text(encoding="utf-8").splitlines():
        if line.strip():
            q = json.loads(line)
            if q["query_id"] in base_qrels:
                qtext[q["query_id"]] = q["text"]
    runs = load_or_build_runs(qtext, args.runs_cache, args.refresh_runs)

    raters = sorted({la["annotator"] for la in labels})
    scenarios: list[tuple[str, list[dict], int, str]] = [
        ("baseline (mean, t>=2)", labels, 2, "mean"),
        ("threshold t>=1", labels, 1, "mean"),
        ("threshold t>=3", labels, 3, "mean"),
        ("recalibrated (severity-removed)", recalibrate(labels), 2, "mean"),
        ("optimistic (max per pair)", labels, 2, "max"),
        ("pessimistic (min per pair)", labels, 2, "min"),
    ]
    for r in raters:
        scenarios.append((f"drop {r}", [la for la in labels if la["annotator"] != r], 2, "mean"))

    results = []
    for name, labs, thr, agg in scenarios:
        qrels = qrels_from_labels(labs, agg)
        h, _ = hypotheses(runs, qrels, thr)
        h["scenario"] = name
        h["alpha_ordinal"] = round(alpha_ordinal(labs), 3)
        results.append(h)

    # bootstrap on baseline
    base_rel = relevant_sets(base_qrels, 2)
    pq = {v: per_query_metrics(runs[v], base_qrels, base_rel) for v in VARIANTS}
    boot = bootstrap(pq, sorted(base_qrels), b=args.bootstrap)

    # stratified nDCG@5 (leakage control + query buckets) on baseline qrels
    query_bucket = {}
    for line in args.pairs.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            query_bucket[r["query_id"]] = r.get("query_bucket")
    strat = stratified(runs, base_qrels, 2, query_bucket)

    report = {"scenarios": results, "bootstrap": boot, "stratified": strat,
              "n_bootstrap": args.bootstrap, "seed": SEED}
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    h1r, h1n = f"H1_recall@{H1_K}", f"H1_ndcg@{H1_K}"
    h2r, h2n = f"H2_recall@{H2_K}", f"H2_ndcg@{H2_K}"
    print("\n=== Sensitivity: H1 (hybrid-dense @10) & H2 (instructional-hybrid @5) ===")
    print(f"  {'scenario':<34}{'nQ':>4}{'alpha':>7}{'H1 rec':>9}{'H1 ndcg':>9}"
          f"{'H2 rec':>9}{'H2 ndcg':>9}")
    for h in results:
        print(f"  {h['scenario']:<34}{h['n_queries']:>4}{h['alpha_ordinal']:>7.2f}"
              f"{h[h1r]:>+9.3f}{h[h1n]:>+9.3f}{h[h2r]:>+9.3f}{h[h2n]:>+9.3f}")

    print(f"\n=== Paired query bootstrap (B={args.bootstrap}, seed {SEED}) ===")
    for k, c in boot.items():
        print(f"  {k:<16} mean {c['mean']:+.3f}  95% CI [{c['ci95'][0]:+.3f}, {c['ci95'][1]:+.3f}]"
              f"  P(>0)={c['frac_positive']:.3f}")

    print("\n=== Stratified nDCG@5 (leakage control + buckets) ===")
    print(f"  {'group':<22}{'n':>4}{'dense':>8}{'hybrid':>8}{'ped':>8}{'H1':>8}{'H2':>8}")
    for g in strat["by_source"] + strat["by_bucket"]:
        print(f"  {g['group']:<22}{g['n']:>4}{g['dense_ndcg@5']:>8.3f}{g['hybrid_ndcg@5']:>8.3f}"
              f"{g['ped_ndcg@5']:>8.3f}{g['H1_ndcg@5']:>+8.3f}{g['H2_ndcg@5']:>+8.3f}")
    print(f"\nreport -> {args.out}")


if __name__ == "__main__":
    main()
