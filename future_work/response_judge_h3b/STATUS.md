# STATUS — response judge (H3b, future work)

**Not part of the 30 June 2026 submission.** Parked here on 2026-06-26.

## What this is

The **original-H3** LLM-as-judge: scores a full tutor **response** to a Terminale C
question on **four criteria** (factual accuracy, curriculum alignment, pedagogical
quality, language register), **1–5 each**, via one schema-constrained Claude call
(`claude-opus-4-8`, variant-blind). See `README.md` and `judge.py`.

## What it is NOT

It is **not** the reframed-H3 **relevance assessor** (the *executed* H3). That one
scores **(query, chunk)** pairs on the **0–3** relevance rubric to validate the
retrieval evaluation, lives conceptually in `src/eval/relevance/` + a not-yet-built
LLM scorer, and is specified in `thesis/m9_relevance_assessor.md`. Different annotation
object, different rubric, different scale. The two were conflated in the 2026-06-26
repo audit; this folder exists to keep them apart.

## Build state

- **BUILT + unit-tested** (offline, no network): `judge.py`, `prompts.py`, `test_judge.py`.
- **BLOCKED — cannot run:** requires a **(query, response)** teacher gold set that was
  **never generated or dispatched** (the 2026-06-26 reframe confirmed only the
  (query, chunk) relevance package was ever sent). Without that gold there is nothing
  to calibrate the judge against.
- **Rubric draft:** `RUBRIC.md` per-level descriptors are **v0.1 draft** (task #13),
  unsigned-off.

## To resume (if the original H3 / H3b is ever executed)

1. Finalize the 4-criterion response rubric descriptors (task #13).
2. Generate ~150 (query, response) pairs and dispatch response-grading annotation
   (tasks #11, #16-responses) → teacher gold.
3. Calibration split (#18); run judge on the gold; compute judge–teacher α /
   per-criterion κ + judge test–retest reliability (#22–23).

## Imports

Self-contained package; tests use relative imports and pass offline. Run from the
repo root, e.g. `pytest future_work/response_judge_h3b/`.