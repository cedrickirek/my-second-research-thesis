## M6. Generation and faithfulness

**Generation**. The tutor answers a single question against the retrieved context using a frontier LLM. The generator is Claude Sonnet 4.6, called once per question (no multi-turn, no tool use), with decoding fixed at temperature 0 (`src/generation/client.py`). The five retrieved passages are passed in full, numbered `[1]…[5]` in fused-rank order (`src/generation/prompts.py`); no per-chunk truncation is applied, as even the longest chunks fit comfortably within the context window. The generator is built and its prompt was chosen by the controlled comparison below, but no answer to an evaluation query is generated or evaluated in this thesis; that evaluation is specified in §M10.


**The V2 strict-faithfulness prompt**. Because the corpus is OCR'd and ~15% of chunks carry a hallucination flag (§M3), the generator must not quietly "fix" its sources. The adopted prompt (V2) tells the model to report the retrieved extracts faithfully, even when they look mathematically wrong, and to raise any suspected error in a separate note, never to silently correct the source. This preserves curriculum authority (the student is being prepared against a specific textbook, §1.1) while still surfacing likely OCR errors for human review.

V2 was selected over a more lenient prompt (V1) and a stricter one (V3, which forbids any comment) in a controlled comparison run under the generator's actual decoding (Sonnet 4.6, temperature 0, 1,024-token cap). Each prompt answered three single-extract questions, three times each (27 calls): an extract containing an error the model can recognise (the textbook's |b| ≤ |a| changed to the false |b| ≥ |a|), one containing an error it cannot recognise (a tile size in a BAC exercise changed from 25 cm to 24 cm), and an unaltered extract (the definition of divisibility). The pass rule was fixed before running: report the extract and flag the error on the first; report the extract on the second; answer correctly without a false alarm on the third.

| Extract | V1 (lenient) | V2 (strict) | V3 (hard) |
|---|---|---|---|
| Error the model can recognise | overrides the source and attributes its correction to [1]; no flag (0/3) | reports the source, flags the error (3/3) | reports the source, no flag (0/3) |
| Error it cannot recognise | reports the source (3/3) | reports the source (3/3) | reports the source (3/3) |
| Unaltered extract | correct, no false alarm (3/3) | correct, no false alarm (3/3) | correct, no false alarm (3/3) |

V2 is the only prompt that passes all three (`experiments/2026-10-21-prompt-ablation-temp0/`; this supersedes an earlier single-run probe at the API's default temperature, `experiments/2026-06-01-baseline-smoke-test/`). With three items, this checks that the prompt behaves as designed; it is not a quantitative estimate of faithfulness.

A known limitation follows directly from the second row: no prompt flagged the error the model had no means to recognise. V2 can only flag errors the model has prior knowledge to detect; an error in content it has not seen, such as a wrong number in an exercise or a mis-OCR'd coefficient, passes through silently (§5.6). Two smaller observations: V2 does not always obey its own rule against adding examples (one of three answers on the unaltered extract added a worked example; V1 did so in all three), and no answer approached the 1,024-token cap (longest: 275 tokens), though these short questions do not settle whether long worked solutions would be truncated.

