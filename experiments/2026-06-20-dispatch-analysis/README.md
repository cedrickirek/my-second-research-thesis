# Dispatch analysis — agreement (H3) + retrieval metrics (H1/H2)

Turns returned teacher labels into the headline evaluation numbers. Runs once
the dispatch labels come back; the building blocks are tested library modules in
`src/eval/relevance/` (`agreement.py`, `qrels.py`, `retrieval_metrics.py`).

## What `analyze.py` does

1. **Ingest** label files — `load_labels` accepts both formats:
   - static-HTML exports: `disp10_T0x_*.jsonl` (`pair_id`, `annotator_id`, `relevance`)
   - web-app export: `annotations.csv` (`source`, `annotator_code`, `relevance`)
2. **Agreement (H3)** — Krippendorff's α (ordinal) over the anchor (pairs graded
   by ≥2 teachers), plus 2-rater readouts (exact/adjacent/weighted κ).
3. **Qrels** — aggregate raters per pair (round-half-up mean); relevant = ≥ 2.
4. **Retrieval metrics (H1/H2)** — re-run the 4 variants (bm25 / dense / hybrid /
   instructional) on the judged queries, score Recall@k, nDCG@k, MRR, and report
   **H1** (hybrid − dense) and **H2** (instructional − hybrid) deltas.

Writes `report.json` + a console table.

## Run

Smoke test on the pilot labels (2 raters, 5 queries — toy numbers, proves the
pipeline end to end):

```
uv run python experiments/2026-06-20-dispatch-analysis/analyze.py \
    --labels "experiments/2026-06-18-pilot-annotation/pilot_T0*.jsonl"
```

Real run, once the 10 teachers return their files (drop them somewhere and glob):

```
uv run python experiments/2026-06-20-dispatch-analysis/analyze.py \
    --labels "path/to/disp10_T*.jsonl"
# or the web-app CSV:
uv run python experiments/2026-06-20-dispatch-analysis/analyze.py --labels "path/to/annotations.csv"
```

`--k 5 10` sets the cutoffs; `--queries` / `--corpus` default to the repo's eval
set and corpus. The dense variant reuses the warm e5-large cache.

## Caveats / decisions

- **Unjudged chunks count as relevance 0** (standard pooled-qrels assumption; the
  pool already includes every retriever's candidates, so misses are rare).
- **instructional** returns ~5 selected chunks by design, so its Recall@10 is
  bounded by that selection — that's the H2 precision/grounding tradeoff, read it
  alongside nDCG, not as a like-for-like depth comparison.
- α is the teacher–teacher ceiling. The **judge-vs-teacher** α (the rest of H3)
  compares the LLM judge's labels against this human gold once the judge is run.
