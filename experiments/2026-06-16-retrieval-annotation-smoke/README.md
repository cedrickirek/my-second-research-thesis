# Retrieval-annotation pairs — smoke run (#12 format validation)

Smoke output of [`src/eval/relevance/build_pairs.py`](../../src/eval/relevance/build_pairs.py),
to validate the #12 format and the 4-variant pooling end-to-end. **Not** the
real annotation pool.

`pairs.jsonl` — 44 (query, chunk) pairs for the **first 3 BAC-2025 queries**,
pooling BM25 + dense + hybrid + instructional (top-10 each, union). Built on the
**e5-small placeholder** model; `relevance` is blank (to be annotated).

Reproduce:
```bash
uv run python -m src.eval.relevance.build_pairs \
  --queries experiments/2026-06-16-query-set-build/queries_bac2025.jsonl \
  --out experiments/2026-06-16-retrieval-annotation-smoke/pairs.jsonl --limit 3
```

The real run waits on the production embedding model + the curated ~100 queries
(see `src/eval/relevance/README.md` § Gating).
