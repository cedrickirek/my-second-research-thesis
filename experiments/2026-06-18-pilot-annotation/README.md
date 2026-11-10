# Pilot annotation (#15) — 2 teachers, static HTML

A no-server pilot of the relevance rubric. Two teachers (T01, T02) each grade
the **same 80 pairs** (5 stratified queries) so we can measure preliminary
agreement, find where the rubric is ambiguous, and lock **v0.1 → v1.0** before
the full dispatch. Chosen over the web app: a self-contained HTML file needs no
database, no hosting, and renders the math.

## Files

- `build_pilot_html.py` — generator (deterministic). Reads the pilot assignment
  (`../2026-06-18-overlap-design/assignments_pilot.json`),
  `results/relevance_pairs.jsonl`, and the rubric; writes the two HTML files.
- `annotation_T01.html`, `annotation_T02.html` — what you send the teachers.
- `analyze_pilot.py` — run **after** the teachers return their files.

## How a teacher uses it

1. Open `annotation_TXX.html` in a browser (Chrome / Edge / Firefox).
   **Needs internet** the first time, to load the math renderer from a CDN.
2. For each passage under a question, click a score **0–3** (rubric is at the
   top, foldable). Add a note if a case felt ambiguous — those notes are gold for
   fixing the rubric.
3. Progress **autosaves in the browser** — they can close and reopen the same
   file on the same computer without losing work.
4. When done, click **« Exporter mes notes »** → it downloads
   `pilot_TXX_YYYY-MM-DD.jsonl`. They email that one file back.

The files are **variant-blind**: which retriever proposed a chunk is not shown,
so the score isn't biased by it.

> **Before sending:** open `annotation_T01.html` yourself and check one question
> renders (math as real symbols, not `$...$`). If a teacher must work offline,
> regenerate with an inlined math library instead of the CDN.

## How you collect + analyze

1. Drop the two returned files (`pilot_T01_*.jsonl`, `pilot_T02_*.jsonl`) into
   this folder.
2. Run:

   ```
   uv run python "experiments/2026-06-18-pilot-annotation/analyze_pilot.py"
   ```

   It reports coverage, agreement (exact / adjacent / binary-relevant / Cohen's
   kappa / weighted kappa) and — most useful — the **disagreement list** with
   each query, chunk, and both teachers' notes. Each disagreement is a candidate
   rubric ambiguity.

3. Walk the disagreements with the rubric, decide the rule, and revise
   `src/eval/relevance/RUBRIC.md` to **v1.0**. Pilot labels were made under v0.1
   and are for calibration only — not final gold.

## Regenerate

```
uv run python "experiments/2026-06-18-pilot-annotation/build_pilot_html.py"
```

Identical output each run (pairs grouped by query; chunk order is a stable hash
of `pair_id`, same for both teachers but decorrelated from retrieval rank).