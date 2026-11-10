## 2026-06-04 — V2 strict-faithfulness prompt adopted as canonical

Decision: The generation system prompt is the "V2" strict-faithfulness prompt
(`src/generation/prompts.py:SYSTEM_PROMPT`). It instructs the model to report
the retrieved extracts faithfully — even when they look mathematically wrong —
and to raise any suspected error only in a separate note, never to silently
correct the source.

Rationale: A 3-prompt ablation on the Chapter 2 smoke-test corpus
(`experiments/2026-06-01-baseline-smoke-test/prompt_ablation.py`) deliberately
corrupted a chunk's `|b| ≤ |a|` to the false `|b| ≥ |a|`. Under a lenient
prompt the model overrode the source with the correct fact from memory and
mis-attributed it to the extract. Faithfulness scaled monotonically with
instruction strictness; V2 reported the source faithfully and flagged the
suspected error separately — preserving curriculum authority while still
surfacing likely OCR/source errors for human review.

Known limitation: V2 only flags errors the model has prior knowledge to detect.
Errors in content the model has not seen pass through silently. This is a
documented limitation, not a bug; the standing grounding check must therefore
include an injection in content the model cannot sanity-check.

Reversibility: If a larger faithfulness evaluation (multiple injected errors ×
repeated runs × model sizes) shows V2 underperforms, revisit prompt design or
move trust enforcement to the corpus layer (hallucination flags + OCR review).

Evidence quality: the 3-prompt ablation was a single run per prompt on one
corrupted item, collected at the API default temperature. Illustrative, not a
quantitative result; see `writeup/methodology.md` §5.

---

### Amendment 2026-10-21 — re-run at temperature 0 (supersedes the evidence above)

The ablation was re-run under the generator's actual decoding
(`claude-sonnet-4-6`, temperature 0, max_tokens 1024): V1 / V2 / V3 × 3
single-extract items × 3 repeats = 27 calls
(`experiments/2026-10-21-prompt-ablation-temp0/`; items, corruptions and the
pass rule were fixed in its `config.yaml` before running). Items: an error the
model can recognise (`6-ciam-tc-0048`, `\le` → `\ge`), an error it cannot
(`bac-2022-maths-tc-0007`, tile size 25 cm → 24 cm), and an unaltered control
(`6-ciam-tc-0045`).

Result (`scoring.csv`; scored by Claude from `results.jsonl`, accepted by
Cedric): V2 is the only prompt that passes all three items in all repeats —
faithful and flagged on the recognisable error, faithful on the unrecognisable
one, no false alarm on the control. V1 overrode the source and attributed its
correction to [1] in 3/3, with no flag; V3 was faithful but silent, by design.
**The decision stands.**

What the re-run adds:
- The silent-passthrough limitation is now observed, not only reasoned: all 9
  answers on the unrecognisable error reproduced 24 cm without comment. This
  meets the "Known limitation" requirement above (an injection in content the
  model cannot sanity-check).
- V2 does not always obey its no-added-examples rule (1/3 on the control added
  a worked example). No answer approached the 1,024-token cap (max 275), which
  does not settle truncation on long worked solutions.

Evidence quality: 3 items × 3 repeats — a behaviour check of the prompt, not a
quantitative faithfulness estimate. Cost: $0.09.