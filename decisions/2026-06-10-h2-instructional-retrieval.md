## 2026-06-10 — H2 instructional retrieval: composition & feasibility

**Status:** Locked (2026-06-10). Source: Tutorly Thesis project chat. Full spec
for #9 (instructional retrieval); feeds #53 Methodology, #54 Results,
#55 Discussion.

### Feasibility gate (PASSED)
- 141 example-type chunks, full corpus coverage.
- Theory↔example co-occurrence: 68% (baseline) → 74% (post tag-recovery, option A).
- Gate criterion: example supply sufficient for the worked-example slot across
  the corpus. Met.

### Composition split
- Top-5 to generator = 3 theory-type + 2 example-type.
- Fixed, NOT tuned (tuning would convert the hypothesis test into a
  hyperparameter search).
- Rationale: the example slot is the intervention; 2 slots give it weight
  without starving the theoretical grounding needed for correctness.

### Fallback rule
- No example-type chunk in the candidate pool for a query → backfill the slot
  with the next-ranked theory-type chunk. Instructional always returns 5.
- Effect: graceful degradation to the hybrid baseline on no-example queries.
- Log every fallback firing. Fallback rate is a reported result.

### Retrieval policy: tag-only
- Example slot retrieves by `content_type == example` (semantic match within
  the tag).
- Tag-or-content rejected: it would muddy the ablation (would measure semantic
  retrieval, not instructional structure).
- Residual risk: headingless worked examples are not cleanly recoverable by the
  tag. Reported as a limitation, not chased. (Measured size below.)

### Eval-stage notes (for #27 / #30)
- Fallback fires on ~26% of theory-bearing leçon queries → a ceiling on the
  aggregate H2 effect. Report the effect size CONDITIONED on
  example-availability, not just the marginal average, or the contribution is
  understated.
- Baseline contamination: pre-recovery, some examples sat in `theory`, so the
  hybrid baseline accidentally pulls worked examples into top-5. The H2 contrast
  is therefore UNDERSTATED. If H2 wins, it wins despite a contaminated baseline.
  State in Discussion.

### Comparison framing
- H2 = instructional vs. hybrid (the H1 winner). Instructional is a
  composition/selection layer over the SAME fused candidate pool — only the
  selection policy differs.

---

### Repo verification & measured residual (2026-06-10, as implemented)

Numbers above checked against the working tree:
- 141 `example` chunks — `data/corpus/chunks.jsonl`, Data Card v2.1 §2.1. ✓
- Co-occurrence 68% → 74% —
  `experiments/2026-06-10-official-corpus-build/h2_feasibility.json`
  (pre 63/93, post 66/89). ✓
- Fallback ceiling ~26% = gap leçons 23 / 89 theory-bearing = 25.8%. ✓

Measured size of the tag-only residual (the limitation this record reports but
does not chase): a bodies-read audit (n = 40 of 190 `theory` chunks, seed 42)
estimates **~32%** are headingless worked examples (95% CI 20–48%; ≈ 62 of 190
— ≈ 28 standalone worked problems + ≈ 33 fragments of a function-study whose
parent is already example-tagged). This sizes two claims the record relies on:
- "residual not cleanly recoverable by tag" (Retrieval policy) — it is ≈ 28
  standalone worked examples, not negligible;
- "baseline contamination → H2 understated" (Eval-stage) — ≈ 28 worked examples
  remain retrievable as `theory`, so the hybrid baseline can still surface them;
  the H2 contrast is understated by at least that much.

Audit detail: `experiments/2026-06-10-official-corpus-build/h2_feasibility.md`
§Q3; Data Card §5.6.


---

### Amendment 2026-06-11 — example-type includes `solution`

`example-type` is **{example, solution}**, not `example` alone (revises the
"Retrieval policy" line above). A `solution` chunk is worked-out content, so it
fits the worked-example slot. Effect: worked-side supply 141 → 174 (141
`example` + 33 `solution`), so the example slot fills more often and fallback
fires less. Implemented in `src/retrieval/instructional.py` (`EXAMPLE_TYPES`).
The §Feasibility co-occurrence numbers (68% → 74%) already counted solutions as
example-side, so they are unchanged. `theory-type` is unchanged —
{theory, theorem, definition, proof, remark} — and `exercise` is in neither slot.
