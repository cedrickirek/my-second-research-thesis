## 2026-06-04 — Generation temperature locked at 0 for evaluation runs

Decision: `src/generation/client.py` defaults to `temperature = 0` for all
evaluation runs.

Rationale: Near-deterministic output is required for reproducibility and for
inter-rater (teacher / LLM-judge) calibration — answers must not drift between
runs of the same input. During smoke testing, the same lenient-prompt input
produced differing behaviour across two runs at the default temperature (one
run flagged the injected error, the other did not).

Tradeoff accepted: Temperature 0 is near-greedy, NOT bit-identical-deterministic
— API-side non-determinism remains, so identical reruns may still differ
slightly. Variance characterization at higher temperatures is out of scope for
now. Note the earlier 3-prompt ablation was collected at the default
temperature; it should be regenerated at 0 if ever cited as a reproducible
result.

Reversibility: Raise temperature deliberately for any experiment specifically
studying output variance; evaluation runs stay at 0.