# Query set build (task #10)

Curate the ~100-query evaluation set for H1/H2 retrieval eval. This set is what
teachers annotate for relevance (#12 → #16) and what every retrieval variant
(dense, BM25, hybrid, instructional) is scored on (#24–28). Design is locked in
the Week-4 brief; this folder is execution.

## Buckets (~100 total)
- ~50 single-leçon (BAC-derived + synthesized)
- ~30 multi-notion (require 2+ leçons in one question — multiple *concepts*, not
  parts a/b/c)
- ~20 hard/edge (under-represented leçons + leçons where H2's fallback fires)

## Stratification
Across the **10 CIAM chapters as-is** (decision 2026-06-16: skip the formal
12-leçon / 3-compétence framing; the corpus carries no compétence labels). Floor
~6–8 queries per chapter. Synthesized queries fill what the BAC under-samples.

| slug | leçon | BAC-2025 single | needs synth fill |
|---|---|---:|---|
| 6_ciam_tc   | Arithmétique dans Z          | 0 | yes (single) |
| 56_ciam_tc  | Nombres complexes            | 2 | top up |
| 172_ciam_tc | Dénombrement et probabilités | 1 | top up |
| 194_ciam_tc | Limites et continuité        | 0 | yes (single) |
| 214_ciam_tc | Dérivation                   | 0 | yes (single) |
| 234_ciam_tc | Primitives et ln             | 2 | top up |
| 256_ciam_tc | Fonction exponentielle       | 0 | **yes — no BAC at all** |
| 276_ciam_tc | Suites numériques            | 0 | yes (single) |
| 296_ciam_tc | Calcul intégral              | 2 | top up |
| 322_ciam_tc | Équations différentielles    | 0 | **yes — no BAC at all** |

## Sources
- **BAC: held-out most-recent year only (2025).** Segmented by hand from
  `data/ocr/bac-2025-maths-tc/`. Questions-only (no solutions needed for the
  query set). **NOTE / open item:** bac-2025 is currently *indexed* (6 chunks,
  `bac-2025-maths-tc-0000…0005`). Cedric is OCR'ing BAC 2020+2021 to add to the
  corpus and will exclude 2025 from the index, restoring the "held-out, never
  indexed" premise. The query set assumes that exclusion lands before retrieval
  eval runs.
- **Synthesized:** LLM-draft ~80 candidates, hand-filter with math-tutor friend
  down to target. Over-generate then cut.

## Hard rules
- **Leakage** (synthesized only): TEST a concept, never COPY a corpus worked
  example's problem statement. If a draft echoes a chunk → rewrite. BAC-derived
  queries are structurally clean once 2025 is de-indexed.
- **Coverage:** stratify across the 10 chapters; floor ~6–8 per chapter.
- **Geometry excluded:** corpus has no geometry theory, so no geometry queries
  (dropped BAC-2025 Ex1.1/1.4/1.6 and Ex3 entirely).
- **Figures:** flag `requires_figure`; default-exclude from eval unless the text
  carries the full problem (BAC-2025 Ex6 kept with flag for review).

## Schema (queries.jsonl, one object per line)
```json
{
  "query_id": "bac2025-e2-1",
  "text": "Si h est continue et paire sur [-3;3], à quoi est égale ∫_{-3}^{3} h(t) dt ?",
  "bucket": "single_lecon",          // single_lecon | multi_notion | hard_edge
  "question_type": "exercise",        // exercise | conceptual (see below)
  "lecons": ["296_ciam_tc"],          // chapter slug(s); 2+ for multi_notion
  "source": "bac",                    // bac | synthesized
  "source_detail": "BAC série C 2025, Exercice 2, item 1",
  "held_out_year": 2025,              // null for synthesized
  "requires_figure": false,
  "difficulty": "medium",             // easy | medium | hard (synthesized only)
  "candidate": true,                  // true until tutor-filter accepts (synthesized)
  "notes": "rationale / leakage-check / difficulty note",
  // --- filled downstream, left empty here ---
  "gold_chunks": [],                  // #12: chunk_ids judged relevant by teachers
  "example_available": null,          // H2: set during eval (instructional layer)
  "fallback_expected": null           // H2: leçon has theory but no paired example
}
```
`gold_chunks` / `example_available` / `fallback_expected` are placeholders that
#12 (retrieval run) and #16 (teacher annotation) populate. #10 only fills the
query side.

## question_type & the conceptual/exercise dimension (2026-06-16)
`question_type` is **orthogonal** to `bucket`: bucket measures *retrieval stress*
(how many leçons a query forces into top-k), question_type measures *what the
student wants*.
- `exercise` — "solve / compute / prove this." Crisp relevant chunks → carries
  the retrieval metrics (#24–28). Most of the BAC-derived set.
- `conceptual` — "help me understand why X." Fuzzy retrieval relevance, but the
  real student use and where curriculum-faithful **pedagogy / register / curriculum
  alignment** get tested at generation time (#29–31). Student register, not exam
  imperative ("Je n'ai pas compris pourquoi…").

**Target mix: ~20% conceptual / ~80% exercise**, applied per chapter.

**Why this split is safe (eval-set routing):** conceptual queries need not carry
retrieval-relevance labels. Retrieval metrics (#24–28) run on the labelled
exercise-leaning subset; generation eval (#29–31) runs on the *full* set incl.
conceptual. Recommended eval-set option **(b)**: generation set = full ~100,
retrieval-metrics set = labelled exercise subset. (Not yet pinned in a
`decisions/` doc.)

## Decisions for this build (2026-06-16)
- Held-out query year = BAC 2025; Cedric OCR's 2020+2021 into the index and
  excludes 2025 (restores "held-out, never indexed").
- Stratify across the 10 CIAM chapters as-is (no formal 12-leçon / 3-compétence).
- **Ungrounded baseline:** kept via H4 (#47, DiD ungrounded-vs-grounded). Cedric
  commits to running H4 rather than promoting an ungrounded arm into #29–31. This
  is the *only* comparison answering "why not just ChatGPT" — H4 is now
  load-bearing, not droppable.
- question_type added; ~20% conceptual / ~80% exercise per chapter.

## Files
- `queries_bac2025.jsonl` — 10 BAC-2025-derived queries (held-out year).
- `queries_synthesized.jsonl` — 166 LLM-drafted candidates, leakage-checked per
  chapter, **uncurated** (`candidate: true`). To be cut by Cedric + math-tutor
  friend (tutor-filter checklist in the brief).
- final merged + curated set → `data/eval/queries.jsonl` (after tutor-filter).

## Candidate pool status (2026-06-16) — over-generated, pre-tutor-filter

176 candidates total (10 BAC + 166 synthesized). 20% conceptual / 80% exercise.

| bucket | have | target | note |
|---|---:|---:|---|
| single_lecon | 113 | ~50 | over-generated; cut to ~50 |
| multi_notion | 42 | ~30 | over-generated; cut to ~30 |
| hard_edge | 21 | ~20 | on target |

Per-leçon appearances (incl. multi-notion mentions), floor ~6–8 cleared
everywhere: arith 26, expo 31, prim/ln 24, integral 24, limites 23, deriv 22,
suites 22, équa-diff 19, complexes 18, proba 15.

**hard_edge composition:** H2-fallback (theory-only) leçon targets — continuité/
monotonie (194), notation exp/trig des complexes (56), dérivées trigonométriques
(214), sous-sections exponentielles (256) — per
`experiments/2026-06-10-official-corpus-build/h2_feasibility.md` §3; plus
under-BAC-sampled arithmetic. Fallback targets flagged in each row's `notes`.

**Next:** tutor-filter (leakage / authenticity / difficulty) → cut to ~100 →
write to #12 (query, retrieved-chunks) annotation format. A few synthesized notes
carry "leakage check best-effort" where a chapter section (IPP, valeur moyenne,
ln limits) was not fully re-read — verify those at tutor-filter.
