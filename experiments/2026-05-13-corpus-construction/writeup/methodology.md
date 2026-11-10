# Corpus construction for the Tutorly RAG tutor: chunking, metadata, and known-failure tagging

**Date:** 2026-05-13
**Scope:** Chapter 2 ("Divisibilité dans Z") of the CIAM Terminale C textbook, post-OCR.
**Pipeline component:** `src/corpus/` (chunking, metadata, figure detection, hallucination filters, build CLI).
**Output artifact:** `data/corpus/chunks.jsonl` — 84 typed chunks. Documented in `data/corpus/DATA_CARD.md`.

---

## 1. Motivation

The Tutorly tutor retrieves curriculum-grounded chunks of Ivorian
Terminale C mathematics content to answer student questions. Section §4
of the OCR validation report establishes that the marker pipeline
produces usable but imperfect markdown: prose CER of 11.5 %, equation
F1 of 87.1 %, but with two systematic failure modes (dropped figures
and structurally suspect equations) that the raw markdown does not
expose to downstream code. Before any retriever can index this corpus,
three questions must be answered:

1. **What is a chunk?** A retriever can only return the units it was
   given. The chunking strategy therefore determines what the LLM can
   ever see in its context window.
2. **What does the retriever know about each chunk?** Hypothesis
   **H2** of this thesis — *instructional retrieval, which pairs a
   theory chunk with its worked example at query time, beats standard
   semantic retrieval* — is impossible without a clean per-chunk
   `content_type` label. Tagging must happen at corpus construction,
   not at query time.
3. **What is known to be wrong with each chunk?** The OCR pipeline
   drops figures and occasionally hallucinates equations. Hiding those
   failures inside the corpus and letting them surface as noisy
   retrieval results would inflate the apparent error of the
   downstream system. Flagging them at build time isolates the OCR
   contribution from the retrieval contribution in later ablations.

This section defines the chunking and metadata schema, the
hallucinated-equation filter, the figure-drop tagger, and the data
card. All five artifacts are produced by the same build script and
together form **v1 of the Tutorly retrieval corpus.**

## 2. Design decisions

Four decisions are load-bearing for the experiments that follow.

| Decision | Choice | Alternative considered | Rationale |
|---|---|---|---|
| Chunking unit | Section-aware, one logical unit per chunk | Fixed-size window (e.g. 512 tokens, 64-overlap) | Fixed-size mixes content types within a single window, which makes a clean `content_type` label impossible and breaks H2's theorem ↔ example join. The cost — variable chunk size — is absorbed by BM25 and modern French dense encoders. |
| `content_type` taxonomy | 8 values: `theory`, `definition`, `theorem`, `proof`, `example`, `exercise`, `solution`, `remark` | 4 values (theory, example, exercise, solution) | The 8-value taxonomy preserves the theorem/proof and definition/example distinctions that H2 depends on, while remaining small enough to be assigned by a heading-keyword classifier rather than an LLM. Adding `remark` as an 8th value captures CIAM's frequent `# Remarque` blocks, which are explanatory but not load-bearing theory. |
| Hallucination handling | Flag, never drop | Drop chunks above a threshold | The v1 corpus is one chapter; dropping noisy chunks shrinks the index materially. Flags expose the failure to downstream code, which can filter at retrieval or eval time without losing recall at index time. |
| Figure handling | Tag, never drop | Drop chunks containing figure references | Same recall argument as above. A chunk that contains both a figure and useful prose remains retrievable; only questions whose answer depends on the figure are unanswerable, and those will be excluded by the evaluation rubric instead. |

## 3. Methodology

### 3.1 Chunking algorithm

The chunker walks the OCR'd markdown top-down and distinguishes two
heading classes:

* **Topic headings** are numbered: `# 2 Divisibilité dans Z`,
  `# 2.1. Multiples et diviseurs`. They carry the curriculum hierarchy
  and feed the `topic` / `section_path` metadata fields. They do **not**
  themselves emit a chunk.
* **Content headings** are keyword headings: `# Définition`,
  `# Propriété 1`, `# Démonstration`, `# Exemples`, `# Remarque`.
  Each begins a new chunk and determines its `content_type`.

Formally, let $H = (h_1, \dots, h_n)$ be the sequence of `#`-prefixed
heading lines in the document, $B_i$ the body of text between $h_i$
and $h_{i+1}$ (with $B_n$ extending to the end of the document), and
$T(h)$ the topic-stack update implied by $h$. The chunker emits one
chunk $C_i = (h_i, B_i, \mathrm{meta}_i)$ for every content heading
and updates the topic stack only on numbered headings:

$$
\mathrm{section\_path}_i \;=\; \begin{cases}
T(h_i) \circ \mathrm{section\_path}_{i-1} & \text{if } h_i \text{ is a topic heading} \\
\mathrm{section\_path}_{i-1} & \text{otherwise}.
\end{cases}
$$

The stack update $T$ replaces the suffix of the stack at depth
$\mathrm{depth}(h_i)$, where $\mathrm{depth}$ is the number of dots
in the section number ("2.1.3" → depth 3). This handles both pushes
(new sub-section) and pops (return to a shallower depth).

### 3.2 Content-type classification

Classification is heading-only and uses lower-cased, accent-stripped,
markdown-emphasis-stripped prefix matching against a fixed keyword
table:

| Keyword (folded) | `content_type` |
|---|---|
| `definition` | `definition` |
| `theoreme`, `propriete`, `proposition`, `lemme`, `corollaire` | `theorem` |
| `demonstration`, `preuve` | `proof` |
| `exemple` | `example` |
| `exercice`, `probleme` | `exercise` |
| `solution`, `corrige` | `solution` |
| `remarque`, `note`, `notation` | `remark` |
| (none of the above) | `theory` (fallback) |

`theory` is a deliberate catch-all. A chunk labelled `theory` is the
classifier saying *"I did not recognise the heading keyword"*, not
necessarily *"this is theoretical material"*; in practice it captures
real explanatory headings like `# Notation`, `# Convention`, and
`# Ensemble des multiples d'un entier relatif`. The data card flags
this and recommends a manual audit before H2 evaluation.

### 3.3 Metadata schema

Every chunk carries the metadata in Table&nbsp;1. The six fields
required by the H2 retriever are bolded.

**Table 1.** Per-chunk metadata schema (`src/corpus/metadata.py`).

| Field | Type | Source |
|---|---|---|
| `chunk_id`              | str   | Stable id `<document-slug>-NNNN`. |
| **`subject`**           | str   | Build CLI argument (`"mathematics"` in v1). |
| **`level`**             | str   | Build CLI argument (`"Terminale C"`). |
| **`topic`**             | str   | `section_path` joined with `" > "`. |
| **`source`**            | str   | Free-text citation, e.g. `"CIAM Terminale C, Chapitre 2"`. |
| **`content_type`**      | enum  | Result of the heading classifier (§3.2). |
| **`has_dropped_figure`**| bool  | True if §3.5 detected a figure reference. |
| `section_path`          | list[str] | Curriculum hierarchy as a list, e.g. `["Divisibilité dans Z", "Multiples"]`. |
| `heading`               | str   | Original heading text, preserved for audit. |
| `char_count`            | int   | Cleaned chunk text length. |
| `word_count`            | int   | Unicode word count over the cleaned text. |
| `equation_count`        | int   | LaTeX equations extracted from the chunk. |
| `hallucination_flags`   | list[str] | Names of filters that fired (§3.4). |

The schema is a frozen `dataclass` with slots, serialised to JSON
Lines (one chunk per line) so the corpus is consumable by any
language's standard JSON parser.

### 3.4 Hallucinated-equation filter

The filter is intentionally rough: it operates on the chunk text and
the equations extracted by the same regex used in the OCR validation
metrics, and it produces a set of named flags that downstream code can
inspect. No chunk is ever dropped.

Five flags are computed; each captures a failure mode observed in the
worst-case marker output (cross-reference: §4.4 error taxonomy in the
OCR validation report).

**Table 2.** Hallucination flags.

| Flag | Detector | Failure mode captured |
|---|---|---|
| `mismatched_delimiters`        | Odd count of unescaped `$` in the chunk. | OCR misreads one boundary of an equation. |
| `unbalanced_braces`            | Any extracted equation has `{` count ≠ `}` count. | Truncated `\frac`, missing argument brace. |
| `equations_without_prose`      | Chunk has ≥1 equation but < 30 chars of prose after stripping. | Chunk cannot be retrieved by paraphrase queries. |
| `suspicious_short_equation`    | Any extracted equation is ≤ 2 chars. | OCR noise like `$.$`, `$-$`, `$•$`. |
| `layout_artefact_in_equation`  | Equation contains `\bullet`, `-Si`, or a bare French connector (`Si`, `donc`, `alors`) as a word. | Prose has bled into the LaTeX (e.g. `\bullet - 81 \equiv 0 [9]`, `-Si\ A = A'`). |

Two further OCR failure modes documented in the validation report —
Greek-letter confusion (`\Delta` ↔ `\Lambda`) and stripped
parenthetical labels (`(\Delta')` → `\Delta`) — are **not** detectable
from the chunk text alone and would require semantic comparison
against the ground truth. They contribute to the residual ~12 % tail
of below-`s = 0.95` matched-equation similarity and remain a known
limitation.

### 3.5 Figure-drop tagging

Marker emits a markdown image reference of the form
`![](_page_<n>_<Picture|Figure>_<m>.jpeg)` wherever the source PDF
contained a figure, but it does **not** OCR the figure's content; the
pixels are saved as a sidecar JPEG and the markdown loses whatever
information was in the figure. The detector is a single regex that
matches this filename pattern and ignores ordinary markdown images
(e.g. logos referenced by URL).

The chunker calls the detector on the raw segment body. If at least
one reference is found, `has_dropped_figure` is set to `True` and the
reference is stripped from the chunk text so it does not pollute
downstream prose-quality metrics. The chunk is **not dropped**: any
text surrounding the figure remains retrievable.

### 3.6 Data card

The corpus ships with a Markdown data card
(`data/corpus/DATA_CARD.md`) following the spirit of Gebru et al.
(2021) and Mitchell et al. (2019). The card documents motivation and
intended use, composition (chunk count, content-type breakdown,
figure-drop rate, flag rate), provenance (source PDFs, OCR pipeline,
chunking decisions), the OCR validation numbers it is anchored on,
known limitations (single-chapter scope, dropped figures, hallucinated
equations, `theory` as fallback, exercises excluded from v1, no
LLM-equivalence calibration), and licensing/ethics constraints. The
card is regenerated by hand whenever the corpus changes; v1 covers
the snapshot reported in §4.

## 4. Results on CIAM Chapter 2

Applying the v1 pipeline to the marker output for CIAM Chapter 2
yields the corpus snapshot in Tables&nbsp;3–4.

**Table 3.** v1 corpus composition.

| Statistic | Value |
|---|---:|
| Documents                                | 1 |
| Chunks                                   | **84** |
| Total prose characters (post-clean)      | 30 785 |
| Total prose words                        | 5 412 |
| Total equations                          | 334 |
| Chunks with dropped figure               | **15** (17.9 %) |
| Chunks with at least one hallucination flag | **6** (7.1 %) |

**Table 4.** Content-type breakdown.

| `content_type` | Count | Share |
|---|---:|---:|
| `theory`     | 30 | 35.7 % |
| `theorem`    | 18 | 21.4 % |
| `example`    | 10 | 11.9 % |
| `remark`     | 10 | 11.9 % |
| `proof`      |  8 |  9.5 % |
| `definition` |  5 |  6.0 % |
| `solution`   |  3 |  3.6 % |
| `exercise`   |  0 |  0.0 % |

Two observations matter for the experiments that follow.

**The H2 join is populated.** With 18 `theorem` and 10 `example`
chunks under the same curriculum sections, the instructional retriever
has material to pair. Whether the pairing improves answer quality is
the empirical question H2 asks; the corpus does not preclude the
answer.

**The fallback bucket dominates.** 35.7 % of chunks classify as
`theory`. Inspection of the heading texts shows that these are
genuinely heterogeneous (`# Notation`, `# Convention`,
`# Ensemble des multiples`, `# Existence`, `# Unicité`,
`# Construction du centre de la rotation`), spanning notational
conventions, sub-proof structure, and minor sub-sections of a larger
theorem. A manual audit before H2 evaluation will either re-classify
the most common headings into one of the seven specific buckets or
accept the heterogeneity as a property of CIAM's section structure.

The hallucination-flag distribution is reported in Table&nbsp;5. None
of the chunks tripped the `mismatched_delimiters` or
`suspicious_short_equation` filters in v1; the dominant failure modes
are equations without enough surrounding prose to be retrievable
(typically section headers immediately followed by a one-line formula)
and layout artefacts where French connectors have bled into the LaTeX.

**Table 5.** Hallucination flag incidence (n = 84 chunks).

| Flag | Chunks fired |
|---|---:|
| `mismatched_delimiters`        | 0 |
| `unbalanced_braces`            | 1 |
| `equations_without_prose`      | 3 |
| `suspicious_short_equation`    | 0 |
| `layout_artefact_in_equation`  | 3 |

## 5. Limitations

The v1 corpus is one chapter of one textbook. The figure-drop rate of
17.9 % and the hallucination-flag rate of 7.1 % are chapter-specific
and will move once the multi-chapter build lands in Week 2.

The hallucination filter is **syntactic only**. Two chunks that are
mathematically equivalent (one missing brace, identical rendering) are
not treated as equal, and two chunks that are mathematically distinct
(an off-by-one exponent) but string-similar are not flagged. A small
LLM-as-judge pass over a sample of matched pairs would calibrate
edit-distance similarity against mathematical equivalence; that
calibration is part of H3 and out of scope for v1.

The chunker is heading-driven. A document that does not use
French-math section headings — for example, a BAC paper whose
numbered exercises are formatted differently — will fall back to the
catch-all `theory` class for most of its content. Adapting the
classifier to BAC formatting is a Week-2 task.

Exercises were excluded from CIAM Chapter 2's OCR run by design so
that the OCR validation comparison stayed scope-matched. As a
consequence the v1 corpus contains zero `exercise` chunks. Until the
multi-document build lands, H2's instructional retrieval cannot pair
theorems with full BAC-style exercises.

## 6. Reproducibility

```bash
# Build the v1 corpus from the OCR'd markdown:
python -m src.corpus.build \
  --input draft_codes/ocr_validation_results/content/output_md/extract_ciam_tc/extract_ciam_tc.md \
  --source "CIAM Terminale C, Chapitre 2 — Divisibilité dans Z" \
  --level "Terminale C" \
  --subject "mathematics" \
  --out data/corpus/chunks.jsonl

# Run the unit tests for chunker, metadata, filters, and figure detection:
pytest src/corpus/ src/ocr/
```

The build is deterministic given the input markdown and CLI arguments.
44 unit tests guard the chunking, metadata, filter, and figure
detectors against regression. The output is a JSON Lines file
consumable by any retrieval indexer; v2 will switch the artifact format
only if a downstream constraint requires it.

## 7. Code map

| Module | Responsibility |
|---|---|
| `src/corpus/metadata.py` | `ContentType` enum, `ChunkMetadata`, `Chunk` dataclasses; JSON serialisation. |
| `src/corpus/chunking.py` | Heading parsing, topic-stack maintenance, content-type classifier, chunk assembly. |
| `src/corpus/filters.py`  | Five hallucination flags; pure functions, no I/O. |
| `src/corpus/figures.py`  | Marker figure-reference detector and stripper. |
| `src/corpus/build.py`    | CLI entry point; reads markdown, writes `chunks.jsonl`, logs summary. |
| `src/corpus/test_*.py`   | 31 unit tests across the four modules above. |
| `data/corpus/DATA_CARD.md` | Human-readable data card v1. |