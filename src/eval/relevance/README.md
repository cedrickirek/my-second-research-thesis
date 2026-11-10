# Retrieval-relevance annotation format (task #12)

Generates the **(query, retrieved-chunk) pairs** teachers annotate for relevance.
The graded labels are the **gold relevance** for the H1/H2 retrieval metrics —
Recall@k and nDCG@k, k ∈ {3,5,10} (#24-28). Built by
[`build_pairs.py`](build_pairs.py).

This format is the **durable data contract**. The teacher-annotation website
(`src/eval/teacher_annotation/`) adapts its input to this schema, not the
reverse: the schema is designed for what the eval needs; the UI is a
presentation layer over it.

## Relevance scale — graded 0–3 (decided 2026-06-16)

The **full annotator-facing definition, decision rules, and examples live in
[`RUBRIC.md`](RUBRIC.md) (v0.1)** — that is the source of truth teachers use.
Summary of the scale: 0 non pertinent · 1 marginal · 2 utile · 3 central.

Graded supports **nDCG@k** (uses the grades) and **Recall@k** (binarise at
`relevance >= 2`, per the rubric). The two locked policy calls: a same-method
worked example with different numbers can score **3**; theory genuinely needed to
answer scores **2**.

Every generated pair is stamped with `rubric_version` (currently `v0.1`) so labels
stay traceable to the definition in force. Bump it in `build_pairs.py` whenever
`RUBRIC.md` changes. Revision plan: pilot (#15) → revise → lock `v1.0` for
dispatch (#16).

## Pooling (how candidates are chosen)

For each query, union the **top-`pool_depth` (default 10)** of every variant:
**BM25 + dense + hybrid + the instructional selection**. Pooling across all
variants keeps the gold labels **variant-neutral** — no variant is advantaged by
being the only source of judged chunks (standard TREC-style pooling). Typical
yield: ~10–25 unique chunks/query.

- **Blind to variant.** `retrieved_by` and `rank_hybrid` are stored for analysis
  but **must be hidden from annotators** — seeing which system retrieved a chunk
  biases judgments.
- **Figures.** Chunks with `has_dropped_figure=True` are excluded by default
  (CLAUDE.md figure policy); `--include-figures` overrides.

## Record schema (pairs JSONL, one object per (query, chunk))

```json
{
  "pair_id": "bac2025-e2-1__296-ciam-tc-0007",
  "query_id": "bac2025-e2-1",
  "query_text": "...",
  "query_bucket": "single_lecon",
  "query_question_type": "exercise",
  "query_lecons": ["296_ciam_tc"],
  "chunk_id": "296-ciam-tc-0007",
  "chunk_text": "...",
  "chunk_content_type": "theory",
  "chunk_topic": "...",
  "chunk_source": "...",
  "chunk_heading": "...",
  "retrieved_by": ["bm25","hybrid","instructional"],  // HIDE from annotator
  "rank_hybrid": 3,                                    // HIDE from annotator
  "rubric_version": "v0.1",  // rubric in force for this label (see RUBRIC.md)
  "relevance": null,        // annotator: 0|1|2|3
  "annotator_id": null,     // anonymised id (names never enter the repo)
  "annotated_at": null,
  "notes": null
}
```

## Gating — why the real run waits

The pool depends on two upstream items not yet final:
1. **Curated ~100 queries** — the #10 pool is over-generated and uncurated;
   the tutor-filter cut comes first.
2. **Production French embedding model** — `e5-small` is a placeholder. The dense
   pool (and thus which chunks teachers judge) shifts with the model, so building
   on the placeholder would force re-annotation. Run for real after the model is
   chosen.

Until then: build + smoke-test only. `--no-dense` pools BM25 alone (no model) to
validate format/logic — **not** a valid annotation pool.

## Run

```bash
# Smoke (BM25 only, no model download):
uv run python -m src.eval.relevance.build_pairs \
  --queries experiments/2026-06-16-query-set-build/queries_bac2025.jsonl \
  --out experiments/2026-06-16-retrieval-annotation-smoke/pairs_bm25only.jsonl \
  --limit 3 --no-dense

# Full (BM25 + dense + hybrid + instructional; downloads e5-small):
uv run python -m src.eval.relevance.build_pairs \
  --queries <curated_queries.jsonl> \
  --out results/relevance_pairs.jsonl
```

## Downstream

teachers annotate `relevance` → overlap design (#14) + pilot (#15) → dispatch
(#16) → agreement stats (#19-21) and retrieval metrics (#24-28). Anonymise on
ingest: annotator names never enter the repo (CLAUDE.md).
