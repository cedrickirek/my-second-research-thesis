# H4 — Grounding and the frontier-vs-SLM gap (exploratory)

> **Status:** exploratory result, drafted 2026-06-30. Numbers are from
> `h4_results.json` (Gemini-2.5-Pro judge over 120 responses). **The judge is
> uncalibrated for response grading** — teacher response-grades were not
> collected within the project window — so this is reported as exploratory.
> Reframed-H3 validated the LLM-judge approach on the *relevance* task, lending
> indirect plausibility only. Do **not** present these CIs as a validated,
> human-aligned effect.

## Hypothesis and operationalization

H4 as originally stated: *grounding closes the quality gap between a frontier
model and a small (~8B) open-weight model.* We test a 2×2 design — {grounded,
ungrounded} × {frontier = Claude Sonnet 4.6, SLM = Mistral 7B} — over **30
Terminale C queries** (figure-dependent queries excluded), generating 120
responses with the canonical V2 faithfulness prompt and hybrid retrieval
(BM25 + e5-large, RRF, top-5). *Grounded* = retrieved extracts injected;
*ungrounded* = identical prompt and question with no retrieved context. Each
response was scored 1–5 by a cross-family judge (Gemini 2.5 Pro) on the four
locked criteria, given the retrieved curriculum passages as reference context.

For each query *q* and criterion *c*:

- `gap_grounded   = frontier_grounded   − slm_grounded`
- `gap_ungrounded = frontier_ungrounded − slm_ungrounded`
- **`delta_gap = gap_ungrounded − gap_grounded`** — *positive* would mean
  grounding *closes* the gap (the H4 prediction).
- `slm_lift = slm_grounded − slm_ungrounded` (the mechanism).

95% CIs by paired bootstrap over the 30 queries (B=10 000, seed=42), matching
the H1/H2 inferential method. `*` = 95% CI excludes 0.

## Headline result: H4 is NOT supported — grounding *widens* the gap

On the 4-criterion mean, `delta_gap = −2.03` (95% CI [−2.47, −1.57], P>0 = 0.000).
The sign is the **opposite** of the H4 prediction: grounding does not close the
frontier–SLM gap, it **widens** it. The mechanism is asymmetric uptake of the
retrieved context:

| metric (4-crit mean) | estimate | 95% CI | reading |
|---|---|---|---|
| gap, ungrounded | −0.13 | [−0.50, +0.23] | ~0: both models poor, indistinguishable |
| gap, grounded | **+1.89** | [+1.51, +2.28] * | frontier pulls clearly ahead |
| **delta_gap (H4)** | **−2.03** | [−2.47, −1.57] * | gap **widens** with grounding |
| frontier lift | **+2.49** | [+2.16, +2.77] * | Claude exploits context strongly |
| SLM lift | +0.47 | [+0.10, +0.83] * | Mistral lift real but small |

Raw means tell the story plainly: **ungrounded**, frontier 2.18 / SLM 2.32 (a
dead heat, both weak); **grounded**, frontier 4.67 / SLM 2.78. Grounding lifts
both models, but the frontier model captures ~5× the benefit.

## Per-criterion breakdown

| criterion | F_ung | F_grd | S_ung | S_grd | delta_gap (H4) | SLM lift |
|---|---|---|---|---|---|---|
| factual_accuracy | 1.17 | 4.57 | 1.43 | 1.63 | −3.20 * | +0.20 (ns, P=.78) |
| curriculum_alignment | 1.53 | 4.93 | 2.63 | 3.23 | −2.80 * | +0.60 (ns, P=.91) |
| pedagogical_quality | 1.03 | 4.20 | 1.47 | 1.83 | −2.80 * | +0.37 * |
| language_register | 5.00 | 5.00 | 3.73 | 4.43 | **+0.70 *** | +0.70 * |

Three readings:

1. **Factual accuracy is the critical failure for the SLM.** Grounding barely
   moves Mistral on facts (+0.20, *not* significant) — it sits at ~1.6/5 even
   *with* the correct extracts in context. Claude, given the same extracts, goes
   1.17 → 4.57. This is the crux: the 7B cannot reliably *use* retrieved
   curriculum to produce factually correct mathematics, even when it is handed
   the right material.

2. **Language is the one criterion where the gap narrows** (`delta_gap`
   positive). This is a **ceiling artifact**, not evidence for H4: Claude already
   scores 5.00 ungrounded (fluent French even when refusing), so it has no room
   to rise; the SLM does rise (3.73 → 4.43), so the gap mechanically shrinks.
   Grounding-as-gap-closer holds only on the criterion where the frontier is
   saturated and the comparison is least about tutoring quality.

3. **Grounding is necessary but not sufficient.** Ungrounded, *both* models are
   near-unusable (means ≈ 2.2). Grounding is what makes the frontier system a
   competent tutor — but the same grounding does not rescue the small model.

## How to frame this in the thesis

- State plainly that **H4 (as originally specified) is not supported**: grounding
  widens rather than closes the frontier–SLM gap, driven by asymmetric
  exploitation of retrieved context (frontier lift +2.49 vs SLM lift +0.47).
- This is a **substantive finding, not a null**: it locates the bottleneck on the
  *generation* side of small models, not the *retrieval* side — retrieval works
  (H1), the frontier uses it (here), but a 7B cannot convert correct context into
  correct mathematics. That is a clean, defensible contribution.
- Keep the **exploratory / uncalibrated-judge** caveat visible on every claim.
- Note the **language ceiling artifact** explicitly so a juror does not read the
  one positive `delta_gap` as partial support.

## Reproducibility

- Generation: `experiments/2026-06-30-h4-grounding-gap/run_generation.py`
  (seed 42, temp 0 both backends) → `responses.jsonl` (120 rows).
- Judge: `gemini_judge.py` (gemini-2.5-pro, temp 0, 4-criterion rubric from
  `future_work/response_judge_h3b/RUBRIC.md`) → `judged.jsonl`.
- Analysis: `analyze.py` (paired bootstrap over queries, B=10 000, seed 42) →
  `h4_results.json`.

### Limitations (carry into the writeup)

- **Uncalibrated judge** for response grading (primary caveat).
- **Single SLM** (Mistral 7B) and **single frontier** (Claude Sonnet) — results
  may not generalize across model families; one-model-per-tier is exploratory.
- **N=30 queries**, Terminale C only.
- **Ungrounded condition under the V2 faithfulness prompt** pushes models toward
  refusal when context is absent; the ungrounded scores partly reflect that
  prompt regime, not raw parametric ability. Described as a design choice, not a
  confound to hide.
- Judge **test–retest reliability not yet measured** (run a subset ≥2× for the
  final writeup).
