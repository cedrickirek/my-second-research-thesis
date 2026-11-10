# Full dispatch annotation (#16) — 10 teachers, static HTML

The real teacher annotation, under the **locked rubric v1.0**. Same tool as the
pilot, scaled out: one self-contained `.html` per teacher, no server/DB.

- `build_dispatch_html.py` — generator (uses `src/eval/relevance/annotation_html.py`).
- `disp10/annotation_T01.html … annotation_T10.html` — what you send the 10 teachers.
- Design: `../2026-06-18-overlap-design/assignments_disp10.json`
  (anchor 10 q × 2 graders + coverage 90 q × 1 → **~11 questions / ~172 pairs each**).

## Dispatch

1. Send **one file per teacher**: T01 → teacher 1, T02 → teacher 2, … Keep the
   `T0x → real name` mapping **privately, outside the repo** (anonymization rule,
   `CLAUDE.md`). The files themselves carry only `T0x`.
2. Teacher opens the file in a browser (**needs internet** for the math renderer),
   grades each passage 0–3 (rubric folded at top), and clicks **« Exporter mes
   notes »** → downloads `disp10_T0x_YYYY-MM-DD.jsonl`. They email it back.
3. Autosaves to the browser; they can stop and resume on the same machine.

> **Before sending:** open `disp10/annotation_T01.html` yourself and check the
> math renders. If a teacher must work offline, ask me to inline KaTeX.

Anchor queries (double-graded) are interleaved with coverage by a per-teacher
hash, so a teacher cannot tell which of their questions are also graded by
someone else. Variant-blind: which retriever proposed a chunk is never shown.

## Collecting + analysis (next session — not built yet)

Gather the returned `disp10_T0x_*.jsonl`. The dispatch analyzer (to build) will:

1. **Join** all 10 files on `pair_id`; recover the retrieval method by joining to
   `results/relevance_pairs.jsonl` (`retrieved_by`, `rank_hybrid`).
2. **Qrels** for H1/H2: a chunk is relevant if `relevance >= 2` (rubric §seuil);
   nDCG uses the graded 0–3.
3. **Agreement (H3)**: Krippendorff's α (ordinal) over the **anchor** (10 queries
   × 2 graders) — the teacher–teacher ceiling, and later judge-vs-teacher.
4. Feed retrieval metrics #24–28 (H1 hybrid vs dense, H2 instructional vs hybrid).

## Contingency

If only ~5 teachers materialise:

```
uv run python "experiments/2026-06-19-dispatch-annotation/build_dispatch_html.py" --design disp05
```

→ `disp05/annotation_T01.html … T05.html` (anchor 10 × 3, ~24 q / ~375 pairs each).

## Regenerate

```
uv run python "experiments/2026-06-19-dispatch-annotation/build_dispatch_html.py"
```

Deterministic. Stamps `rubric_version: v1.0` on every exported label.
