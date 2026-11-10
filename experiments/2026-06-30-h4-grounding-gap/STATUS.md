# STATUS: PILOT ONLY — NOT A THESIS RESULT

**Decision (2026-06-30): the numbers in this folder are NOT used in the thesis.**
H4 is submitted as *specified-but-not-executed methodology, results deferred to
future work* (consistent with the 2026-06-20 writeup-scope decision).

## Why the results were not used

A diagnostic audit (`_audit.py`) found the experiment, as built, does **not**
cleanly test H4 ("grounding closes the frontier-vs-SLM gap"). The
operationalization of the *ungrounded* condition is confounded:

- The strict V2 faithfulness prompt forbids answering without extracts. So in the
  ungrounded cell the **frontier model refuses 73% of the time** (22/30) — its
  low ungrounded score measures *refusal*, not mathematical ability.
- The **SLM refuses 0%** — it answers anyway and **fabricates citations** (24/30
  ungrounded responses cite `[n]` extracts that were never provided).
- So the ungrounded condition compares *"frontier refuses"* vs *"SLM
  hallucinates"* — not the effect of grounding on capability.
- Retrieval quality leaks in: the **grounded frontier still refused 30%** (9/30),
  i.e. when retrieved chunks lacked the answer.
- Frontier grounded factual-accuracy is near-binary (26×5, plus 1/3×low),
  limiting how meaningful the means are.

The aggregate `Δgap = −2.03` is arithmetically real but reflects this
prompt-compliance artifact, not a valid grounding effect.

## Future-work fix (if H4 is executed properly later)

- Use a **separate ungrounded prompt** that permits parametric answering, so the
  ungrounded cell measures capability, not prompt compliance.
- Add a **second SLM** (e.g. Gemma) as a cross-family robustness check.
- **Calibrate the response judge** against teacher response-grades before relying
  on its scores.
- Measure judge **test–retest reliability**.

## Artifacts (kept for reproducibility, not citation)

- `run_generation.py`, `responses.jsonl` — 120 generated responses (valid).
- `gemini_judge.py`, `judged.jsonl` — Gemini-2.5-Pro scores (uncalibrated).
- `analyze.py`, `h4_results.json` — bootstrap (confounded, see above).
- `RESULTS_DRAFT.md` — superseded by this STATUS note; do not cite.
