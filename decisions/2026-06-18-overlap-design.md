# Teacher-annotation overlap design (task #14)

Date: 2026-06-18

## Decision

Annotate the 1565 #12 relevance pairs with a **two-tier overlap design**,
assigned **by query** (a query's ~15.7 pairs always stay with one grader, so
context isn't fragmented):

- **Anchor (agreement) tier** — a stratified-random **10 queries** (~157 pairs)
  graded by **2 teachers** each. Feeds Krippendorff's α: teacher–teacher
  ceiling and judge–teacher calibration (**H3**).
- **Coverage tier** — the other **90 queries** (~1408 pairs) graded by **one**
  teacher each. Feeds the retrieval ground-truth qrels (**H1/H2**).

**Revised 2026-06-18 (load reduction).** The first cut (anchor 20×5, coverage
80×1) put ~283 pairs on each teacher. Cedric judged that too heavy, so the
design was rebalanced to **~11 queries / ~172 pairs per teacher** (−39%): a
smaller **10-query × 2-rater** anchor + 90 single-graded coverage. All 100
queries are still covered (covering every query is why it's 11, not 10, queries
each). Trade-offs accepted: anchor redundancy drops 5 → 2 (the pilot showed 2
raters already give a usable α = 0.70), and the 10-query anchor spans 7 of 10
chapters rather than all 10. Numbers below reflect the revised design.

A **pilot precedes dispatch** (task #15): 2 teachers grade a small stratified
set, we measure preliminary agreement, fix rubric ambiguities, and lock the
rubric **v0.1 → v1.0** before the full run.

Generated deterministically (seed 42) by
`experiments/2026-06-18-overlap-design/build_assignments.py` →
`assignments_{pilot,disp10,disp05}.json`.

## Why this shape (evidence)

- **Pooling + per-(query,chunk) relevance judging** is the standard IR
  evaluation method (TREC since 1992; qrels; BEIR for the RAG era). The pairs
  outnumber the queries because each query retrieves many candidate chunks, and
  relevance is a property of the (query, chunk) pair.
- **Redundancy belongs only on the anchor.** Agreement (α) is only defined where
  graders overlap; coverage pairs need one good label. The literature puts the
  useful redundancy at **2–3 raters/item** (floor), up to 3–5 (sweet spot). The
  revised design uses **2** to keep load light — defensible, since the pilot hit
  α = 0.70 with 2 raters.
- **The anchor is stratified-random, not hand-picked.** It mirrors the 60/20/20
  bucket split (now **6 single-leçon / 2 multi-notion / 2 hard-edge**), so α
  reflects the task rather than a hard subset. At 10 anchor queries it spans 7 of
  the 10 chapters (a representativeness cost of the smaller anchor).
- **Per-teacher load is the binding constraint, not headcount.** With 10 teachers
  and all 100 queries to cover once, the anchor budget is small; we spend it on
  10 queries × 2 raters so each teacher stays at ~172 pairs.

## The two dispatch options

| | Teachers | Anchor | Coverage | Per-teacher | Total judgments |
|---|---|---|---|---|---|
| **disp10** (recommended) | 10 | 10 × **2** raters | 90 × 1 | ~11 queries, **165–179 pairs** | 1721 |
| **disp05** (contingency) | 5 | 10 × **3** raters | 90 × 1 | ~24 queries, **369–380 pairs** | 1877 |

- **disp10** is the plan. ~172 pairs of quick 0–3 judgments per teacher; the
  10-query × 2-rater anchor gives a usable α (pilot-validated at this redundancy).
- **disp05** is the fallback if only ~5 of the over-recruited 10 materialise
  (over-recruiting is on the project risk list). Anchor goes to 3 raters; with
  half the teachers, per-teacher load roughly doubles (~375 pairs) but is the
  degraded-mode cost.
- Load is balanced within ±7% by greedy pair-count allocation; anchor raters are
  assigned by a sliding window so co-rater pairings vary (better α coverage).

## Pilot (task #15)

`assignments_pilot.json`: **2 teachers, 5 stratified queries (~80 pairs), both
grade all** (redundancy 2). Purpose: exercise the app, surface rubric
ambiguities (where the two disagree → clarify the rule), and lock **v0.1 →
v1.0**. Pilot labels are made under v0.1 and are for process calibration, **not
final gold** — those queries are re-graded under v1.0 at dispatch.

## What is NOT decided here / open

- **Response-scoring items** (the tutor-answer 1–5 criteria, the app's other item
  type) are a separate annotation track; this design covers retrieval-relevance
  pairs only.
- **No LLM pre-labelling of the teacher pass.** Showing teachers a machine grade
  first would anchor them and contaminate H3 (automation/anchoring bias). The
  LLM judge labels pairs only *after* it is calibrated against the clean human
  gold — that ordering is H3 itself.

## App integration (when ready)

The JSON is query-level (canonical). To seed the app
(`src/eval/teacher_annotation/`): load `results/relevance_pairs.jsonl` as
`SEED_ITEMS` (RETRIEVAL type), then expand each teacher's assigned query_ids
into their pair item_ids to build `SEED_ASSIGNMENTS`. Confirm `RELEVANCE_SCALE`
in `app.py` matches the locked rubric (v1.0) before dispatch. Do this against a
fresh DB (delete `annotations.db` / point at clean Postgres).

## Reversibility

Re-run the generator to regenerate any design (seed 42 → identical output).
Anchor size, rater depth, and teacher count are CLI-free constants at the top of
`build_assignments.py` / the `build(...)` calls — change and re-run.
