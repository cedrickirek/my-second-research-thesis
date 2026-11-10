# Annex M. Methodology — supplementary detail

This annex holds methodological detail moved out of Chapter 3 to keep the chapter to its page
budget. Nothing here is new: each item is the long form of a design summarised in the body.

---

## Annex M.A — Relevance rubric: decision rules and worked examples (expands §M7.3)

The 0–3 scale of §M7.3 is applied with seven decision rules that disambiguate the
boundaries the calibration pilot showed were contested (§M7.5). In full:

1. Same-chapter floor. A same-chapter passage scores at least 1 even if a
   solution would not use it. 0 is reserved for a different chapter that
   contributes nothing.
2. Utility overrides topic upward. If a part of the passage genuinely helps with
   a part of the question it scores 2, even when it comes from another chapter,
   and even if a more direct passage exists elsewhere — a passage is not penalised
   because a better one was also retrieved.
3. Method, format, or procedure count (the stepping-stone rule). A passage
   exhibiting a step the question requires is useful (2) even if its own content
   is incomplete (e.g. an empty variation table for a function study), and central
   (3) if that method, applied, answers the whole question.
4. Coverage separates 2 from 3. Helping one part scores 2; sufficing for all
   parts scores 3.
5. Each passage is judged alone, never by comparison with the others retrieved
   for the same query.
6. Conceptual questions. For an "explain why…" question, a passage giving the
   explanation, intuition, or proof scores 3, whereas a bare calculation or
   incidental property scores 1.
7. Worked examples accompany the rubric and are reproduced (with the rubric
   itself, in French) in Annex A; the four-level worked example is drawn
   from the integral-parity pilot cluster (§M7.5).

---

## Annex M.B — Calibration pilot and the v0.1 → v1.0 → v1.1 revision (expands §M7.5–§M7.6)

The pilot. A calibration pilot (master task 15) had two teachers
independently grade 80 pairs drawn from 5 stratified queries under rubric v0.1. The pilot was
diagnostic, not a result: its labels are calibration data, explicitly not the final
gold.

What it showed. Weighted κ on the graded scale was 0.704, with 96.2%
adjacent agreement (|difference| ≤ 1) and only three pairs off by two — no wild
disagreement. The binary-relevant (≥ 2) κ was 0.587, the weak point, and it
mattered because ≥ 2 is the Recall threshold. Of 32 disagreements, the 1↔2 boundary
dominated (13), ahead of 0↔1 (8) and 2↔3 (8), clustering on property-heavy,
multi-step queries (an integral-parity BAC item and a function-study item accounted
for roughly half). The diagnosis: v0.1 did not tell teachers how to score a passage
that is "right chapter, similar-looking, but not the property the question needs."

The v1.0 revision (locked 2026-06-18 for the full dispatch) responds
point-for-point:

1. reframes the guiding question to "would a correct solution use this?" and adds the
   "je m'en sers" test for the 1↔2 boundary — the principal fix;
2. sharpens 0↔1, reserving 1 for same-lesson-but-unused and sending
   different-chapter-contributes-nothing to 0;
3. sharpens 2↔3, with 3 = the exact sufficient property/method and 2 = a necessary
   piece needing others;
4. adds the stepping-stone rule (rule 3, Annex M.A);
5. adds the real four-level worked example drawn from the integral-parity pilot
   cluster.

The pilot evidence and each change are recorded in the rubric-v1.0 decision record.

The v1.1 written form (2026-06-27). At dispatch the written v1.0 was accompanied
by oral clarifications on the two contested boundaries: a same-chapter passage
that goes unused scores 1, not 0, and partial utility — a part of a passage
serving a part of the question, including a required method or format — scores 2,
with full coverage scoring 3. Version v1.1 writes these clarifications down. It
does not alter the underlying definition (utility for a correct solution); it fixes its
application on those two boundaries, and it is the version the LLM relevance-assessor is
prompted with (§M8), so machine and panel judge against the same applied definition.
The human gold reflects v1.0 as briefed — the same clarifications were given to all
annotators at dispatch; v1.1 is its faithful written form, not a post-hoc change of standard.

---

## Annex M.C — Overlap design: load balancing, the design revision, and the disp05 contingency (expands §M7.9–§M7.10)

The binding constraint is per-annotator load, not headcount. With the queries to be
covered once and a small anchor budget, the design question is how many quick 0–3
judgements each annotator must make. The design was revised once on exactly this axis.
The first cut — a 20-query × 5-rater anchor plus 80 singly-graded coverage queries
— placed about 283 pairs on each annotator, judged too heavy. It was rebalanced to
the 10-query × 2-rater anchor plus 90 coverage queries used for dispatch, cutting
per-annotator load by roughly 39% to about 11 queries / ~172 pairs each. Every query
is still covered exactly once (covering all 100 is why each annotator carries ~11
queries, not 10). The two trade-offs this revision accepted are explicit: anchor
redundancy dropped from 5 to 2 raters, and the anchor's chapter span narrowed from 10 to
7 (§M7.8) — both justified by the pilot's α = 0.70 at redundancy 2.

Allocation mechanics. Within a tier, load is balanced to within ±7% by greedy
pair-count allocation, and the two anchor raters per query are assigned by a sliding
window so that which pair of annotators co-rates varies across the anchor — giving the
agreement estimate broader coverage of rater pairings than a single fixed pair would.
The whole assignment is generated deterministically (seed 42), so any design variant
is exactly reproducible by re-running the generator.

The realised dispatch (disp10) and the contingency (disp05).

| Option | Annotators | Anchor | Coverage | Per-annotator | Total judgements |
|---|---|---|---|---|---|
| disp10 (realised) | 10 | 10 × 2 raters | 90 × 1 | ~11 queries, 165–179 pairs | 1,720 |
| disp05 (contingency, not used) | 5 | 10 × 3 raters | 90 × 1 | ~24 queries, 369–380 pairs | 1,877 |

The fifteen dispatch identifiers (T01–T15) recorded in the 2026-06-24 handoff do not
indicate fifteen independent grading loads: ten annotators completed the dispatch, and
five further annotators who became available later re-filled five of the ten
assignment files already present (re-grading those slots rather than extending
coverage). Coverage and the design are therefore those of the ten-person disp10; the
five refills are replacement labour on five existing assignments, not a sixth-through-
fifteenth tier.

---

## Annex M.D — Generation-side and student evaluation: full specifications (expands §M10)

Both evaluations below are designs, not results. Both depend on a (query,
response) gold set that was never collected (only the (query, chunk) relevance package
was dispatched; §M7.1, §M8), so neither could be run before submission. They are the
immediate next steps the executed retrieval-and-evaluation foundation was built to
enable, and are carried as future work in Chapter 6.

### Annex M.D.1 — Generation-side evaluation (H2 generation side; the response judge, H3b)

The instrument is the response judge — the original H3, scoring a full tutor
response on four model-independent criteria (factual accuracy, curriculum alignment,
pedagogical quality, language register), 1–5 each, variant-blind, based on a correct
human solution to avoid generator–judge circularity (§2.4, C2). Its scoring harness is
built and unit-tested (Opus 4.8, schema-constrained), but is unrunnable: it needs
teacher response-gold to calibrate
against, and the four-criterion rubric descriptors are still draft v0.1 (task #13). The
specified protocol:

1. finalise the four-criterion rubric;
2. generate ~150 (query, response) pairs and dispatch response-grading annotation;
3. calibrate the judge against that gold (judge–teacher Krippendorff's α / per-criterion
   κ, plus judge test–retest reliability);
4. score responses generated by all four retrieval variants and compare (paired tests,
   §M9).

This is what would test the H2 generation-side claim — does the theory-plus-example
mix yield better answers, not just better retrieval — which §M8 is explicit cannot be
concluded from the retrieval metrics alone. Grounded-vs-ungrounded scoring under this
same judge is also the instrument for H4. Status: harness built; calibration and run
not executed.

### Annex M.D.2 — Student evaluation (field validation)

A small field study with 10–20 Terminale C students, validating the tutor with the
target population rather than against labels. Specified design:

- Session: a fixed problem set, scored for correctness, with pre/post
  confidence ratings and a short interview; a pairwise A/B in which the student
  compares pedagogical vs. standard-hybrid answers blind — structurally a small preference
  arena (cf. §2.4) that yields the student-side H2 signal.
- Run: consent (with parental consent for minors); a 1–2 student pilot to validate the
  protocol; then full sessions.
- Analysis: quantitative (correctness, confidence shift, A/B preference rate) and a
  light qualitative coding of the interviews.

No part is built, and the study needs a human cohort and ethics turnaround it could not
get before the deadline. Status: specified, not executed.

---

## Annex M.E — Retrieval implementation detail (expands §M4)

The three retrieval channels of §M4 are run at untuned defaults; their implementation specifics
are recorded here.

BM25 (sparse). Okapi BM25 via `rank-bm25` at library defaults ($k_1 = 1.5$, $b = 0.75$) —
fixed, like the slot sizes of §M5.2, so the H1 contrast reflects the value of adding a sparse
channel under standard conditions rather than of a tuned one. Tokenisation uses the spaCy French
pipeline [Honnibal & Montani, 2017] with three maths-motivated adjustments: (1) single-character
variables preserved — the stopword filter would otherwise drop length-1 tokens such as "$a$",
"$x$", "$n$", "$k$", which are content-bearing and often the strongest lexical signal in maths;
(2) accent folding (é→e, à→a, ç→c), so an accent-less query ("theoreme") still matches accented
corpus text — a lexical-channel choice only, since the dense channel resolves diacritics in its own
subword tokeniser; (3) no lemmatisation, which would wrongly conflate "limites" (noun) with
"limité" (participle). The index is built once and not rebuilt across experiments.

Dense (multilingual E5). `intfloat/multilingual-e5-large`, a 1024-dim multilingual encoder.
Raw passage and query text is fed to its pretrained subword tokeniser, which is why the BM25
pre-processing applies to the sparse channel only. Per the E5 recipe, queries carry prefix
`query: ` and passages `passage: ` (deviating measurably degrades quality); both embeddings are
L2-normalised and compared by cosine, computed once at index time. The encoder is not
fine-tuned on CIAM: the 100-query set is too small to fine-tune without overfit, and H1 concerns
retrieval channels, not encoder adaptation — fine-tuning would confound the channel-level
comparison.

RRF hybrid. The hybrid fuses the BM25 and dense rankings by Reciprocal Rank Fusion [Cormack et
al., 2009]: $\text{rrf}(d) = \sum_{r \in \{\text{BM25}, \text{dense}\}} 1/(60 + \text{rank}_r(d))$,
with canonical $k = 60$. Each retriever contributes its top-20; the union, re-ranked by the fused
score, is the RRF-fused pool, consumed both by the hybrid (top-5 in fused order) and by the
pedagogical retriever (the same pool, a different selection policy; §M5.3). RRF is preferred over
learned fusion because the labelled data is insufficient to train a fuser without overfit, so the
H1 contrast reads as dense-only vs a standard, untuned hybrid.