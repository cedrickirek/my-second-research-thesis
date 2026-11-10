"""Analyze returned teacher labels: agreement (H3) + retrieval metrics (H1/H2).

Given the exported label files (JSONL from the static-HTML tool and/or CSV from
the web app), this:
  1. computes inter-annotator agreement over the anchor (Krippendorff's alpha),
  2. builds graded qrels (relevant >= 2, rubric v1.0),
  3. re-runs the 4 retrieval variants on the judged queries and scores them,
     reporting H1 (hybrid vs dense) and H2 (instructional vs hybrid).

Smoke-run now on the pilot labels (2 raters, 5 queries):
  uv run python experiments/2026-06-20-dispatch-analysis/analyze.py \
      --labels "experiments/2026-06-18-pilot-annotation/pilot_T0*.jsonl"

Real run (after dispatch returns):
  uv run python experiments/2026-06-20-dispatch-analysis/analyze.py \
      --labels "experiments/2026-06-19-dispatch-annotation/disp10/disp10_T*.jsonl"
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.agreement import summarize  # noqa: E402
from src.eval.relevance.qrels import (  # noqa: E402
    agreement_records,
    build_qrels,
    load_labels,
    relevant_sets,
)
from src.eval.relevance.retrieval_metrics import score_run  # noqa: E402
from src.retrieval.bm25_index import BM25Index  # noqa: E402
from src.retrieval.corpus_loader import load_chunks  # noqa: E402
from src.retrieval.dense_index import (  # noqa: E402
    DEFAULT_MODEL,
    DenseIndex,
    default_cache_path,
)
from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.retrieval.instructional import InstructionalRetriever  # noqa: E402
from src.retrieval.tokenizer_fr import FrenchTokenizer  # noqa: E402

HERE = Path(__file__).resolve().parent
CANDIDATES = 20
VARIANTS = ("bm25", "dense", "hybrid", "instructional")


def variant_runs(qtext, bm25, dense, hybrid, instructional, k):
    """Ranked runs per variant + per-query instructional diagnostics.

    The instructional retriever returns a fixed 5-chunk bundle (3 theory + 2
    example), so its run is capped at 5 — `recall@10 == recall@5` by
    construction. H2 must therefore be compared at a MATCHED cutoff (k=5), and
    conditioned on `example_available` (on example-poor queries the retriever
    backfills toward the hybrid baseline, diluting the effect). We keep that
    bookkeeping here so the H2 analysis can honour the decision record
    (`decisions/2026-06-10-h2-instructional-retrieval.md`).
    """
    runs = {v: {} for v in VARIANTS}
    instr_diag: dict[str, dict] = {}
    for qid, text in qtext.items():
        runs["bm25"][qid] = [h.chunk_id for h in bm25.search(text, k=k)]
        runs["dense"][qid] = [h.chunk_id for h in dense.search(text, k=k)]
        runs["hybrid"][qid] = [
            h.chunk_id
            for h in hybrid.search(text, k=k, candidates_per_retriever=CANDIDATES)
        ]
        res = instructional.search(text, candidates_per_retriever=CANDIDATES)
        runs["instructional"][qid] = [c.metadata.chunk_id for c in res.selected]
        instr_diag[qid] = {
            "example_available": res.example_available,
            "fallback_fired": res.fallback_fired,
            "backfills": res.backfills,
            "n_example_in_pool": res.n_example_in_pool,
            "n_theory": res.n_theory,
            "n_example": res.n_example,
        }
    return runs, instr_diag


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True, help="glob of label files (.jsonl/.csv)")
    ap.add_argument("--queries", type=Path, default=REPO_ROOT / "data/eval/queries.jsonl")
    ap.add_argument("--corpus", type=Path, default=REPO_ROOT / "data/corpus/chunks.jsonl")
    ap.add_argument("--k", type=int, nargs="+", default=[5, 10])
    ap.add_argument("--out", type=Path, default=HERE / "report.json")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    paths = [Path(p) for p in glob.glob(args.labels)]
    if not paths:
        raise SystemExit(f"no label files match {args.labels!r}")
    labels = load_labels(paths)
    logging.info("loaded %d labels from %d file(s)", len(labels), len(paths))

    agr = summarize(agreement_records(labels))
    qrels = build_qrels(labels)
    rel = relevant_sets(qrels, threshold=2)

    qtext = {}
    for line in args.queries.read_text(encoding="utf-8").splitlines():
        if line.strip():
            q = json.loads(line)
            if q["query_id"] in qrels:
                qtext[q["query_id"]] = q["text"]

    chunks = load_chunks(args.corpus)
    bm25 = BM25Index(chunks, FrenchTokenizer())
    dense = DenseIndex(
        chunks, model_name=DEFAULT_MODEL, embeddings_cache=default_cache_path(DEFAULT_MODEL)
    )
    hybrid = HybridRetriever(bm25, dense, rrf_k=60)
    instructional = InstructionalRetriever(hybrid, chunks)

    ks = tuple(args.k)
    runs, instr_diag = variant_runs(qtext, bm25, dense, hybrid, instructional, k=max(ks))
    metrics = {v: score_run(run, qrels, rel, ks=ks) for v, run in runs.items()}

    # H1: hybrid vs dense at the deepest cutoff — both return k chunks, fair.
    kk = max(ks)
    h1_keys = [f"recall@{kk}", f"ndcg@{kk}", "mrr"]
    # H2: instructional is capped at 5 chunks (3 theory + 2 example), so compare
    # at a MATCHED cutoff. Scoring it at k=10 against a 10-item hybrid is an
    # artifact (it cannot fill ranks 6-10), not a finding.
    h2_k = min(ks)
    h2_keys = [f"recall@{h2_k}", f"ndcg@{h2_k}", "mrr"]
    comparisons = {
        "H1_hybrid_vs_dense": {
            k: metrics["hybrid"][k] - metrics["dense"][k] for k in h1_keys
        },
        "H2_instructional_vs_hybrid_matched_k": {
            "k": h2_k,
            **{k: metrics["instructional"][k] - metrics["hybrid"][k] for k in h2_keys},
        },
    }

    # H2 conditioned on example_available: on example-poor queries the
    # instructional retriever backfills toward the hybrid baseline, so averaging
    # over them dilutes the effect (decision 2026-06-10). Re-score both
    # retrievers on the subset whose fused pool held >=1 example-type chunk.
    ea_qids = {q for q, d in instr_diag.items() if d["example_available"]}
    instr_ea = score_run(
        {q: r for q, r in runs["instructional"].items() if q in ea_qids},
        qrels, rel, ks=(h2_k,),
    )
    hybrid_ea = score_run(
        {q: r for q, r in runs["hybrid"].items() if q in ea_qids},
        qrels, rel, ks=(h2_k,),
    )
    comparisons["H2_instructional_vs_hybrid_example_available"] = {
        "k": h2_k,
        "n_queries": instr_ea["n_queries"],
        **{k: instr_ea[k] - hybrid_ea[k] for k in h2_keys},
    }

    n_q = len(instr_diag)
    n_fallback = sum(1 for d in instr_diag.values() if d["fallback_fired"])
    instructional_diagnostics = {
        "n_queries": n_q,
        "n_example_available": len(ea_qids),
        "example_available_rate": len(ea_qids) / n_q if n_q else 0.0,
        "n_fallback_fired": n_fallback,
        "fallback_rate": n_fallback / n_q if n_q else 0.0,
        "mean_backfills": (
            sum(d["backfills"] for d in instr_diag.values()) / n_q if n_q else 0.0
        ),
        "mean_n_example_selected": (
            sum(d["n_example"] for d in instr_diag.values()) / n_q if n_q else 0.0
        ),
    }

    report = {
        "n_label_files": len(paths),
        "n_labels": len(labels),
        "n_judged_queries": len(qrels),
        "agreement": agr,
        "metrics": metrics,
        "comparisons": comparisons,
        "instructional_diagnostics": instructional_diagnostics,
    }
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- console report ---
    a = agr
    print("\n=== Agreement (H3) ===")
    print(f"  Krippendorff alpha — ordinal: {a['krippendorff_alpha_ordinal']:.3f} | "
          f"nominal: {a['krippendorff_alpha_nominal']:.3f}")
    print(f"  units: {a['n_units']} ({a['n_units_multi_rated']} multi-rated) | "
          f"raters: {a['n_raters']}")
    if "two_rater" in a:
        t = a["two_rater"]
        print(f"  [2-rater] exact {t['exact']:.1%} · adjacent {t['adjacent']:.1%} · "
              f"weighted kappa {t['weighted_kappa']:.3f}")

    print(f"\n=== Retrieval metrics (judged queries: {len(qrels)}) ===")
    hdr = "  {:<14}" + "{:>10}" * (len(ks) * 2 + 1)
    cols = []
    for k in ks:
        cols += [f"recall@{k}", f"ndcg@{k}"]
    cols += ["mrr"]
    print(hdr.format("variant", *cols))
    for v in VARIANTS:
        vals = [f"{metrics[v][c]:.3f}" for c in cols]
        print(hdr.format(v, *vals))

    print("\n=== Hypotheses (delta) ===")
    h1 = comparisons["H1_hybrid_vs_dense"]
    print(f"  H1 hybrid-vs-dense (k={kk}): "
          + " · ".join(f"{k} {h1[k]:+.3f}" for k in h1_keys))
    h2m = comparisons["H2_instructional_vs_hybrid_matched_k"]
    print(f"  H2 instructional-vs-hybrid (matched k={h2_k}, all q): "
          + " · ".join(f"{k} {h2m[k]:+.3f}" for k in h2_keys))
    h2e = comparisons["H2_instructional_vs_hybrid_example_available"]
    print(f"  H2 (example-available q only, n={h2e['n_queries']}): "
          + " · ".join(f"{k} {h2e[k]:+.3f}" for k in h2_keys))
    di = instructional_diagnostics
    print(f"  [instructional] example-available {di['n_example_available']}/{di['n_queries']}"
          f" ({di['example_available_rate']:.0%}) · fallback {di['n_fallback_fired']}"
          f" ({di['fallback_rate']:.0%}) · mean backfills {di['mean_backfills']:.2f}")
    print(f"\nreport -> {args.out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
