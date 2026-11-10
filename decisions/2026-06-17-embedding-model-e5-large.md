# Production embedding model: multilingual-e5-large (bge-m3 queued)

Date: 2026-06-17

## Decision

The production dense embedding model is **`intfloat/multilingual-e5-large`**
(560M params, 1024-dim), replacing the `multilingual-e5-small` smoke-test
placeholder. This is the model the *real* retrieval-relevance pair run (#12)
embeds against, so teachers annotate the pool produced by the production model
once.

**`BAAI/bge-m3` is queued as a follow-up**, not adopted now (see below).

## Rationale

- **Best open-weights French retrieval at the E5 prefix convention.** On
  MTEB-French (Ciancone et al. 2024, the standard French embedding benchmark),
  open-weights retrieval NDCG@10: bge-m3 0.81 > Solon-large 0.79 >
  **e5-large 0.76** > sentence-camembert-large 0.72. e5-large is the strongest
  model that is a *drop-in* swap from the e5-small placeholder.
- **Reproducibility is the thesis's core contribution.** Open-weights, runnable
  locally via `sentence-transformers`, no API cost, and no curriculum content
  leaving the machine. API models score higher (text-embedding-3-large 0.86) but
  are closed, paid, and non-reproducible — disqualifying for this thesis.
- **Size is not a constraint.** The corpus is 722 chunks + 100 eval queries; a
  560M model embeds it in seconds-to-minutes. The A100/compute risk in the
  project plan concerns the H4 SLM *generation*, not embeddings.
- **The paper's own finding backs multilingual over French-specific:** large
  multilingual models beat French-specific ones (CamemBERT/Solon) on retrieval.

## Why e5-large now, bge-m3 later (not e5-large permanently)

bge-m3 scores higher (0.81 vs 0.76) but uses a **different, prefix-free**
encoding convention, whereas e5-large uses the **same `query:`/`passage:`
prefixes** as the placeholder — so adopting it is a one-line `DEFAULT_MODEL`
change with zero code risk, and unblocks the #12 dispatch immediately. bge-m3
needs the prefixing made model-aware first; it is the planned next step and may
supersede this choice once integrated and compared head-to-head on our labelled
set.

**H1 caveat for the bge-m3 step:** bge-m3 has internal lexical (sparse)
matching. H1 is "BM25 + dense > dense-only", so when bge-m3 is used its **dense
vectors only** must form the dense arm, or the comparison is confounded.

## What changed

- `src/retrieval/dense_index.py`: `DEFAULT_MODEL` →
  `intfloat/multilingual-e5-large`; module docstring updated. Prefixes unchanged
  (same E5 convention). The cache key includes the model name, so the dense
  cache auto-invalidates and re-embeds on first use.
- `src/eval/relevance/build_pairs.py`: gating docstring + download-size log line
  updated. It instantiates `DenseIndex` without an explicit `model_name`, so it
  inherits the new default.
- `CLAUDE.md`: generation/embedding note + Current focus updated.

Follow-up landed same day (bge-m3 selectability, no run yet):
- `dense_index.py`: `prefixes_for_model` (E5 -> query:/passage:, bge-m3 -> none,
  unknown -> none + warning), `model_slug`, `default_cache_path` (per-model cache
  so models don't clobber each other). Constructor infers prefixes from the model
  name unless given explicitly.
- `build_pairs.py`: `--model` flag (default e5-large); cache path derived per
  model. A bge-m3 pool is now `build_pairs.py --model BAAI/bge-m3` — no code edit,
  no prefix juggling.
- The e5-large cache was migrated to its per-model filename
  (`results/dense_cache/intfloat_multilingual-e5-large.npz`), so the 2026-06-17
  embed is reused, not recomputed.

## Verification

- Unit tests use an injected fake encoder (no download) and remain green.
- Real re-embed + ranking sanity check on e5-large recorded in
  `experiments/2026-06-17-e5-large-swap/` (see that folder's notes).

## Reversibility

One-line change. Revert `DEFAULT_MODEL` to roll back; the cache re-keys
automatically. Switching to bge-m3 (or Solon for an ablation) is the same
constructor swap once the encoding convention is made model-aware.
