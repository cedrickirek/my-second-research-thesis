# e5-large embedding swap — sanity check

Date: 2026-06-17

Verifies the production embedding model swap (multilingual-e5-small placeholder
→ `intfloat/multilingual-e5-large`). See
`decisions/2026-06-17-embedding-model-e5-large.md`. **Not an evaluation** — no
metrics, no ground truth; this only confirms the model embeds the production
corpus and gives topically sensible dense rankings.

## Run

`uv run python experiments/2026-06-17-e5-large-swap/sanity_check.py`

- Corpus: full 722-chunk `data/corpus/chunks.jsonl` (post BAC-2025 de-index).
- Embedded on CPU, 722 passages, ~10.5 min (one-off). Cached to
  `results/dense_cache/passages.npz` (gitignored) — **reused by `build_pairs.py`**
  for the real #12 run (same model + chunk set ⇒ same cache key).
- `run.log` holds the full output (gitignored, verbose HF download logs).

## Result: PASS — rankings topically correct, regression case fixed

Top-1 dense hit per probe (cosine):

| Query | Top-1 | Verdict |
|---|---|---|
| Qu'est-ce qu'une primitive d'une fonction ? | `234/definition` "On appelle primitive de f…" (0.878) | **Fix** — e5-small returned `Propriété`; e5-large returns the Définition at rank 1 |
| module et argument d'un nombre complexe | `56/remark` argument, top-5 all `56` (Nombres complexes), incl. module/argument def | Correct leçon |
| Définition d'une suite arithmétique | `276/definition` "Définitions" (Suites) | Correct leçon + type |
| équation différentielle du 2nd ordre | `322/solution`, top-3 all `322` (Éq. diff.) | Correct leçon |
| propriétés du logarithme népérien | `234/definition` ln; #4 = `234/theorem` **Propriétés** | Correct |

All five return the right leçon; content-types are sensible (définitions and
worked examples surface for "what is / how to" questions). Scores sit in a tight
0.84–0.88 band, normal for in-domain French E5 cosine. This is a clear
improvement over the e5-small placeholder, whose weak ranking on the primitive
query was the motivating regression (`notes/2026-06-11.md`).

## Caveats

- Rankings only; recall/MRR/nDCG await the labelled set (#24–28).
- "suite arithmétique" returned general suite definitions, not an
  arithmetic-specific heading — likely a corpus heading-granularity artifact,
  not a model problem. Revisit if it shows up in real metrics.
