# LLM-as-judge — response scoring (original H3 → future work H3b)

> **STATUS: FUTURE WORK (H3b). NOT part of the 30 June submission.** This is the
> *original-H3* **response judge** (4 criteria, 1–5, scoring full tutor *responses*).
> It is **not** the reframed-H3 **relevance assessor** (0–3, scoring (query, chunk)
> pairs), which is the executed H3 — see `src/eval/relevance/` and `thesis/m9_relevance_assessor.md`.
> Built and unit-tested 2026-06-26; **cannot be calibrated or run** because the
> (query, response) teacher gold was never collected (and the 4-criterion rubric
> descriptors are draft v0.1, task #13). Moved here from `src/eval/judge/` on
> 2026-06-26 to keep future work separate from the executed core. See `STATUS.md`.

Task #17 (judge prompt v1, per-criterion scoring) + the descriptor draft for #13.

Scores a tutor **response** to a Terminale C question on the four locked criteria
— `factual_accuracy`, `curriculum_alignment`, `pedagogical_quality`,
`language_register` — **1–5 each**, via one Claude call constrained to a JSON
schema so the output always parses. Research-only: calibrated against the teacher
gold, never run on students at deployment.

## Files

- `RUBRIC.md` — the 4-criterion rubric. Criteria + 1–5 scale are **locked**
  (match `app.py:RESPONSE_CRITERIA`); the **per-level descriptors are draft v0.1**
  and need sign-off (#13) before judge calibration (#22–23).
- `prompts.py` — system prompt (rubric injected from `RUBRIC.md`, single source of
  truth) + the (question, [reference context], response) user block. Variant-blind.
- `judge.py` — `ResponseJudge.judge(question, response, context=None) → JudgeResult`.
- `test_judge.py` — offline tests (fake client, no network).

## Usage

```python
from future_work.response_judge_h3b import ResponseJudge
judge = ResponseJudge()                       # claude-opus-4-8, reads ANTHROPIC_API_KEY
res = judge.judge(question, response, context=retrieved_passages)
res.scores          # {"factual_accuracy": 4, ...}
res.justifications  # one French sentence per criterion
res.mean
```

## Design notes

- **Model `claude-opus-4-8`** (most capable judge). Opus 4.8 removed
  `temperature`, so it is **not** passed (it would 400); output is constrained by
  `output_config.format`, not a prefill. Requires an `anthropic` SDK new enough to
  support `output_config` — upgrade if a real run rejects it.
- **Determinism.** Opus 4.8 is near- but not bit-deterministic. For calibration,
  run each item ≥2× and report judge **test–retest reliability** rather than
  assuming determinism.
- **Grounding.** Pass the retrieved curriculum passages as `context` so factual
  accuracy and curriculum alignment are judged against the syllabus, not just the
  model's priors — that grounding is the H3 argument.

## Not done here (downstream)

Calibration split (#18), running the judge on the teacher-annotated responses and
computing judge-vs-teacher α / per-criterion κ (#22–23). Those gate on the
finalized response rubric and the returned teacher response-annotations.

## Cost

One judge call per response. **No API call is made by the tests.** Estimate cost
before any batch run (CLAUDE.md hard rule: no paid-API loops without a cost
estimate + confirmation).
