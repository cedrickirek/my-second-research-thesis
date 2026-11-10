# Tutorly Corpus — Data Card v2

**Corpus snapshot:** 2026-06-10
**Build command:** `uv run python "experiments/2026-06-10-official-corpus-build/build_corpus.py"`
**Pipeline version:** `src/ocr/` + `src/corpus/` at this repo's working tree
**Author:** Cedric Kire (MSc thesis, HEC Paris × Polytechnique)

This data card documents the **v2 retrieval corpus** for the Tutorly thesis
RAG tutor. It **supersedes v1** (2026-05-13), which was a single-chapter
pilot. v2 is the first multi-document corpus: ten CIAM Terminale C chapters
plus two **indexed** BAC série C papers (sessions 2022 and 2024), built by
applying the OCR method validated in v1 (marker, see §4) to the full in-scope
document set. The **2025 BAC paper is held out** as the evaluation year and is
**not indexed** — it is the source of the held-out queries in
`data/eval/queries.jsonl`, so indexing it would leak gold answers into
retrieval. See §5.9 and `decisions/2026-06-17-bac-2025-held-out.md`.

The card follows the spirit of Gebru et al. (2021) and Mitchell et al.
(2019): everyone who downstreams this corpus — retrieval ablations,
LLM-as-judge calibration, student evaluation — needs to know what is in it,
how it was made, what it is missing, and what it is known to get wrong.

---

## 1. Motivation

| Field | Value |
|---|---|
| **Purpose** | Provide curriculum-grounded retrieval context for a French-language tutor targeting **Ivorian Terminale C mathematics**. |
| **Created for** | Tutorly MSc thesis hypotheses **H1** (hybrid retrieval > dense), **H2** (instructional retrieval > standard semantic), **H3** (LLM-as-judge calibration), **H4** (grounding closes the SLM gap). |
| **Scope** | Terminale C only. Decision in [`decisions/2026-05-12-scope-terminale-c-only.md`](../../decisions/2026-05-12-scope-terminale-c-only.md). Geometry chapters excluded for now (§5.3). |
| **Not for** | Production tutoring at runtime (research-only artifact). Deployment requires teacher review per chunk and a takedown channel for publisher disputes. |

## 2. Composition (v2 snapshot)

| Statistic | Value |
|---|---|
| Documents (indexed) | **12** (10 CIAM chapters + 2 BAC papers; BAC 2025 held out, see §5.9) |
| Chunks | **722** (706 CIAM, 16 BAC) |
| Total prose characters (post-clean) | 424 010 |
| Total prose words | 75 853 |
| Total equations | 5 313 |
| Chunks with dropped figure | **113** (15.7 %) |
| Chunks with ≥1 hallucination flag | **106** (14.7 %) |
| Empty chunks dropped at build | 91 (§5.5) |

### 2.1 Content-type breakdown

The chunker assigns exactly one `content_type` per chunk from an eight-value
taxonomy. The fallback class `theory` captures explanatory prose under a
heading that matched no other keyword.

| `content_type` | Count | Share |
|---|---:|---:|
| `theory`     | 185 | 25.6 % |
| `theorem`    | 142 | 19.7 % |
| `example`    | 141 | 19.5 % |
| `remark`     |  82 | 11.4 % |
| `proof`      |  57 |  7.9 % |
| `definition` |  48 |  6.6 % |
| `exercise`   |  34 |  4.7 % |
| `solution`   |  33 |  4.6 % |

**Change from v1:** v1 had **zero** `exercise` and three `solution` chunks
(exercises were stripped to scope-match the OCR validation). v2 carries
**34 exercise + 33 solution** chunks — the two indexed BAC papers contribute
12 of the exercises — so H2's theorem ↔ exercise/worked-example retrieval
finally has material on both sides of the join.

**Classifier improvement (option A, 2026-06-10).** The H2 feasibility audit
found ~24 worked examples misfiled as `theory` because their heading was an
imperative ("Résoudre…", "Calculer…") or "Étude de la fonction …" rather than
the keyword "Exemple", plus several keyword headings garbled by OCR drop-cap
loss ("Démonstration" → "émonstration"). The heading classifier
([`src/corpus/chunking.py`](../../src/corpus/chunking.py)) now recognises
those worked-example cues and tolerates a dropped initial letter. Effect:
`example` 117 → **141**, `theory` 224 → **190**, with `proof`/`solution`/
`exercise` each recovering a few. Precision verified: all 24 recovered
examples are genuine worked content (zero theory swept in).

### 2.2 Per-document composition

| Document (slug) | Topic | Chunks | Eq. | Fig-drop | Flagged |
|---|---|---:|---:|---:|---:|
| `6_ciam_tc`   | Arithmétique dans Z (divisibilité, congruences, PGCD/PPCM) | 137 | 511 | 8 | 11 |
| `56_ciam_tc`  | Nombres complexes | 87 | 732 | 17 | 13 |
| `172_ciam_tc` | Dénombrement et probabilités | 70 | 323 | 6 | 5 |
| `194_ciam_tc` | Limites et continuité | 67 | 568 | 19 | 8 |
| `214_ciam_tc` | Dérivation | 53 | 446 | 7 | 14 |
| `234_ciam_tc` | Primitives et logarithme népérien | 67 | 580 | 9 | 9 |
| `256_ciam_tc` | Fonction exponentielle | 70 | 482 | 12 | 18 |
| `276_ciam_tc` | Suites numériques | 51 | 590 | 6 | 7 |
| `296_ciam_tc` | Calcul intégral | 71 | 487 | 24 | 14 |
| `322_ciam_tc` | Équations différentielles | 33 | 451 | 5 | 5 |
| `bac-2022-maths-tc` | BAC série C — session 2022 | 7 | 89 | 0 | 1 |
| `bac-2024-maths-serie-c` | BAC série C — session 2024 | 9 | 54 | 0 | 1 |

**Held out (not indexed):** `bac-2025-maths-tc` (BAC série C — session 2025;
6 chunks, 54 equations). Its OCR is staged in `data/ocr/bac-2025-maths-tc/`
for query provenance but is excluded from the index — it is the held-out
evaluation year (§5.9).

### 2.3 Per-chunk metadata schema

Every chunk carries the fields in [`src/corpus/metadata.py`](../../src/corpus/metadata.py):
`chunk_id`, `subject`, `level`, `topic`, `source`, `content_type`,
`has_dropped_figure`, `section_path`, `heading`, `char_count`, `word_count`,
`equation_count`, `hallucination_flags`. The `hallucination_flags` set gains
one new member in v2 — `ocr_degeneration_loop` (§5.2).

## 3. Provenance

### 3.1 Source documents

CIAM = **Collection Inter-Africaine de Mathématiques**, Terminale C, the most
widely used reference for Ivorian Terminale C classrooms. BAC papers are the
official MENA (Côte d'Ivoire) série C mathematics examinations. Raw PDFs live
under `data/raw/` and are **not committed** (gitignored, copyright).

| Source | Year | Publisher | Status |
|---|---|---|---|
| 10 × CIAM Terminale C chapters (analysis, algebra, probability) | — | EDICEF/NEI | OCR'd, cleaned, chunked, **indexed** |
| 2 × BAC série C math papers (2022, 2024) | 2022–2024 | MENA (Côte d'Ivoire) | OCR'd, cleaned, chunked, **indexed** |
| 1 × BAC série C math paper (2025) | 2025 | MENA (Côte d'Ivoire) | OCR'd, **held out — not indexed** (§5.9) |
| Further BAC papers / corrigés / programme officiel | — | MENA | **Pending** (not yet obtained) |

### 3.2 OCR pipeline

| Stage | Tool | Output | Notes |
|---|---|---|---|
| PDF → markdown + sidecar images | [`marker`](https://github.com/VikParuchuri/marker) (run on Colab GPU, 2026-06-09 trial) | `data/ocr/<slug>/<slug>.md` (+ `_meta.json`) | Equations as `$…$` / `$$…$$` LaTeX. Figures saved as JPEG sidecars; **figure content is not OCR'd**. |
| Degeneration-loop cleaning | [`src/ocr/clean.py`](../../src/ocr/clean.py) | `data/ocr/<slug>/<slug>.clean.md` | Excises vision-model repetition loops (§5.2). Every removal recorded in `results.json`. |
| Chunking + tagging | [`src/corpus/`](../../src/corpus/) | `data/corpus/chunks.jsonl` | This data card describes the output of this stage. |

**`data/ocr/` layout.** Each document folder holds the raw marker output
(`<slug>.md`, tracked), the cleaned canonical text (`<slug>.clean.md`,
tracked — the corpus builds from this), and the marker `<slug>.meta.json`
sidecar (gitignored). `data/ocr/` is the version-controlled OCR source of
truth, sitting between `data/raw/` (PDFs) and `data/corpus/` (chunks).

### 3.3 Chunking strategy

Section-aware, single `content_type` per chunk (unchanged from v1). Topic
headings (numbered, e.g. `# 2.1. …`) feed the curriculum hierarchy; content
headings (keyword, e.g. `# Définition`, `# Propriété 1`, `# Exemples`,
`# EXERCICE 3`) each start a chunk and set its `content_type`. See
[`src/corpus/chunking.py`](../../src/corpus/chunking.py). BAC papers chunk
cleanly because `EXERCICE N` headings map to `content_type = exercise`.

Rationale for section-aware splitting: **H2 (instructional retrieval) is the
novel contribution of this thesis.** It depends on retrieving a theory chunk
*jointly* with its worked example — impossible under fixed-size chunking,
which mixes content types within a window.

## 4. OCR validation: method anchor (no new ground truth in v2)

**v2 collects no new hand-transcribed ground truth.** The 2026-05-12 marker
validation on CIAM Chapter 2 ("Divisibilité dans Z", now part of
`6_ciam_tc`) already established that the *method* is good enough to run on
the full corpus; v2 *applies* that method. The validated numbers below
therefore stand as the **expected** quality of the OCR, not a per-document
measurement (see §5.7 for the honesty caveat).

| Metric (CIAM Ch.2, marker vs. hand-corrected GT) | Value |
|---|---:|
| Prose CER | 11.51 % |
| Prose WER | 14.40 % |
| Equation detection F1 | 87.13 % |
| Equation exact-match (matched pairs) | 87.46 % |

Full methodology: [`experiments/2026-05-12-marker-validation-ciam-tc/writeup/methodology.md`](../../experiments/2026-05-12-marker-validation-ciam-tc/writeup/methodology.md).
A second engine (`docling`) was evaluated and underperformed marker by an
order of magnitude on equations; marker is the pipeline.

**Automated quality sweep (v2, in place of new GT).** The build reports,
per document and in aggregate, the incidence of every hallucination flag and
every degeneration loop removed (`experiments/2026-06-10-official-corpus-build/results.json`):

| Flag | Meaning | v2 incidence (chunks) |
|---|---|---:|
| `layout_artefact_in_equation` | marker bleed (`\bullet`, `-Si`, French connector) in an equation | 40 |
| `equations_without_prose`     | equations with < 30 chars of surrounding prose | 38 |
| `suspicious_short_equation`   | an extracted equation ≤ 2 chars | 23 |
| `unbalanced_braces`           | `{`/`}` mismatch in an equation | 9 |
| `ocr_degeneration_loop`       | a vision-model repetition loop was excised here | 3 |

## 5. Known limitations

Documented loudly so they shape downstream decisions, not buried.

### 5.1 Figures are dropped

Marker emits an image reference but **never OCR's figure content**.
**15.7 % of v2 chunks** carry `has_dropped_figure = true`; questions whose
answer depends on reading a figure are unanswerable from this corpus.
Evaluation builders must filter these out by default (override requires an
explicit flag). Rationale and reversibility:
[`decisions/2026-05-13-figure-handling.md`](../../decisions/2026-05-13-figure-handling.md).

### 5.2 Vision-model degeneration loops (new failure mode in v2)

The 2026-06-09 marker run (LLM/vision mode) occasionally got stuck on an
equation-dense page and repeated a short **English** phrase to a ~2 048-char
token ceiling — e.g. `of the latter` ×145, `the same of` ×169,
`the control of` ×135 — in three chapters (56, 256, 276). The cleaner
([`src/ocr/clean.py`](../../src/ocr/clean.py)) excises any wordy phrase
repeated ≥ 20× consecutively, replacing it with a `⟦OCR_LOOP_REMOVED⟧`
sentinel so the loss is visible and the containing chunk is flagged
`ocr_degeneration_loop`.

- **4 loops removed** (7 301 chars) across 3 documents; **0** near-threshold
  (10–19×) runs needed review.
- **3 chunks** survive carrying the flag (`56-ciam-tc-0042` exercise,
  `256-ciam-tc-0097` theory, `276-ciam-tc-0061` example); the 4th sat in an
  empty chunk that §5.5 then dropped.
- These 3 chunks also retain minor **English bleed** in their headings
  (e.g. "Exercices **with** …"). Per the build decision, they are **flagged,
  not repaired** — a `come-back-later` item, not a blocker. They should be
  excluded from evaluation sets by default.

### 5.3 Geometry excluded (deliberate scope choice)

The CIAM geometry chapters (isometries, similitudes, conics, barycentres,
space geometry) are **not** in v2. Under the figure-drop policy (§5.1) most
geometry chunks would not be self-contained — their meaning lives in dropped
figures. **Consequence (asymmetry):** the BAC papers we *do* include are
geometry-heavy (e.g. 2022 covers isometries, a parabola directrix,
similitudes, 3-D vectors), so the corpus contains geometry *exercises* but no
geometry *theory* to ground them. The labelled query set must therefore avoid
geometry questions, and H2 cannot be tested on geometry. Revisiting geometry
depends on a figure-recovery decision (multimodal captioning or manual
transcription).

### 5.4 Equation error modes the flags do not catch

Structural errors the syntactic flags miss but the validation report
quantifies: Greek-letter confusion (`\Delta` ↔ `\Lambda`), lost decorations
(`\widehat{…}`), and stripped parenthetical labels (`(\Delta')` → `\Delta`).
These contribute to the ~12.5 % below-0.95 equation-similarity tail and
cannot be cheaply flagged at build time.

### 5.5 Empty chunks dropped; descriptive-heading labels not in `section_path`

The chunker emits a chunk per content heading; a descriptive (non-numbered,
non-keyword) heading immediately followed by a sub-heading yields an empty
body. **92 such 0-char chunks were dropped** at build (they carry no
retrievable content; their material lives in adjacent chunks). Side effect:
because only *numbered* headings feed `section_path`, the label of a dropped
descriptive heading (e.g. "Conjugué d'un nombre complexe") is not preserved
in any chunk's `section_path`. A future chunker pass could merge such headings
forward instead of dropping them.

### 5.6 `theory` is a fallback bucket

26.1 % of chunks are `theory` — most are real explanatory prose, but the
class is a catch-all meaning *"the chunker did not recognise the heading
keyword"*. The 2026-06-10 audit + option A (§2.1) drained the heading-
detectable misfiles out of this bucket (a re-audit finds zero remaining
example-like *headings*). **A larger residual of *headingless* worked examples
remains, and it is not small:** a manual audit (n = 40, bodies read, seed 42,
2026-06-10) estimates **~32 % of this bucket are worked examples** whose
heading gives no cue (95 % CI 20–48 %; ≈ 62 of 190 chunks — ≈ 28 standalone
worked problems such as urn/dice probability or solving `34x − 15y = 2`, plus
≈ 33 fragments of a function-study whose parent *is* example-tagged). So the
`example` tag still under-represents worked content at the chunk level; an
example slot that retrieves on the tag alone carries this recall hole. This is
a known, deferred limitation (proceed-and-revisit decision, 2026-06-10), not a
resolved one. A handful of non-curricular BAC preamble lines ("SÉRIE C",
duration/calculator notes) also land here.

### 5.7 No per-document ground truth (validation is method-transfer)

§4's CER/F1 are measured on **one chapter** (Ch.2 divisibility). v2 assumes
that quality transfers to the other 12 documents. This is plausible (same
engine, same publisher, same content types) but **unmeasured**; per-content-
type and per-scan-quality variation is not quantified. Building a small
multi-document GT sample is the natural rigour upgrade if time allows.

### 5.8 LLM-equivalence not measured

The hallucination filters are syntactic; two equation-identical chunks (one
missing brace) are treated as different by string similarity. Calibrating
edit-distance similarity against mathematical equivalence is part of H3 and
out of scope here.

### 5.9 BAC 2025 held out (leakage prevention)

The 2025 BAC série C paper is the **held-out evaluation year**: the 9
`bac2025-*` queries in `data/eval/queries.jsonl` are drawn from it. It is
therefore **deliberately excluded from the index** — were it indexed, those
queries could retrieve their own source items (and, once corrigés are added,
their own solutions), inflating retrieval and end-to-end scores with leaked
gold. Its OCR is kept staged under `data/ocr/bac-2025-maths-tc/` for query
provenance only; the build config (`experiments/2026-06-10-official-corpus-build/config.yaml`)
omits it from the `documents` list, with a comment forbidding re-adding it.
Sessions 2022 and 2024 remain indexed as in-distribution worked material.
Rationale and reversibility: `decisions/2026-06-17-bac-2025-held-out.md`.

## 6. Ethical and licensing notes

| Concern | Status |
|---|---|
| Source copyright | CIAM is published material; BAC papers are public examinations. Corpus is **research-only**, never redistributed. Raw PDFs gitignored. Any thesis-published example must fall under fair use / *courte citation* or have permission. |
| Student data | None ingested at this stage. When teacher/student annotations land, names **never enter the repo** per [`CLAUDE.md`](../../CLAUDE.md). |
| Production use | The tutor will not be deployed to real students before teacher review of retrieved chunks. The LLM-as-judge is research-only. |

## 7. Reproducibility

```bash
# Rebuild the v2 corpus from data/ocr/ (raw marker output, committed):
uv run python "experiments/2026-06-10-official-corpus-build/build_corpus.py"

# The document set, citations, and cleaning thresholds are declared in:
#   experiments/2026-06-10-official-corpus-build/config.yaml
# The run report (per-doc flags, loops, content_type) is written to:
#   experiments/2026-06-10-official-corpus-build/results.json

# Verify the unit tests:
pytest src/ocr src/corpus
```

## 8. Changelog

| Version | Date | Notes |
|---|---|---|
| v1 | 2026-05-13 | First release. Single chapter (CIAM Ch. 2). Marker OCR, section-aware chunking, 8-value `content_type`, rough hallucination flags, figure-drop tagging. |
| v2 | 2026-06-10 | Multi-document: 10 CIAM chapters + 3 BAC papers, 728 chunks. Added `src/ocr/clean.py` degeneration-loop cleaning + `ocr_degeneration_loop` flag; promoted OCR into `data/ocr/`; dropped 92 empty chunks; first `exercise`/`solution` coverage for H2. Geometry deliberately excluded. No new ground truth (method anchored on v1 validation). |
| v2.1 | 2026-06-10 | H2 feasibility audit + classifier improvement (option A): worked-example heading cues (`Résoudre`, `Calculer`, `Étude de …`) + OCR drop-cap tolerance. `example` 117 → 141, `theory` 224 → 190; leçon theory↔example co-occurrence 68 % → 74 %. Chunk count and OCR cleaning unchanged. |
| v2.2 | 2026-06-17 | **BAC 2025 held out (leakage prevention, §5.9).** Removed the `bac-2025-maths-tc` document from the build config so it is no longer indexed; it is the held-out evaluation year (source of the `bac2025-*` queries). Corpus 728 → 722 chunks (`theory` 190 → 185, `exercise` 35 → 34); all 722 retained chunks byte-identical (only the 6 bac-2025 chunks removed). OCR retained under `data/ocr/` for provenance. See `decisions/2026-06-17-bac-2025-held-out.md`. |
