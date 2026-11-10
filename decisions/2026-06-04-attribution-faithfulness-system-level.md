## 2026-06-04 — Attribution faithfulness handled at the system level, not the rubric

Decision: Attribution faithfulness (does the answer correctly represent what the
retrieved source actually says?) is addressed at the system level by the V2
prompt, NOT as a teacher-rubric criterion. The teacher rubric stays at 4
criteria; the LLM-judge calibration stays on the same 4 shared criteria.

Rationale: Teachers grade answers without access to the retrieved chunks, so
they structurally cannot judge whether an answer faithfully represents its
source. Adding an "attribution faithfulness" criterion would ask graders to
evaluate something they cannot see. The system-level mitigation is the V2
prompt; the 3-prompt ablation is the empirical evidence that V2 reduces
misattribution under corrupted-source conditions.

Reversibility: If a future annotation design shows teachers the retrieved
chunks alongside the answer, attribution could become a gradable criterion. Not
planned.

See also: `decisions/2026-06-04-v2-faithfulness-prompt.md`.