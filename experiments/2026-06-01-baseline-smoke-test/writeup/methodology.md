# Baseline hybrid retrieval pipeline: implementation and smoke-test validation

**Status:** Preliminary engineering validation, not an evaluation.
**Date:** 2026-06-01 – 2026-06-03
**Scope:** 10-chunk subset of the v1 corpus (CIAM Terminale C, Chapter 2,
"Divisibilité dans ℤ"). No retrieval-quality metrics are claimed here.
**Pipeline components:** `src/retrieval/` (tokenizer, BM25, dense, RRF hybrid)
and `src/generation/` (French tutor prompt + Claude client).

## 1. Purpose

Hypothesis H1 states that hybrid retrieval (lexical BM25 + French dense)
outperforms dense-only retrieval on this corpus. Testing H1 requires a working
baseline retriever to measure against. This note documents the implementation
of that baseline and an end-to-end smoke test confirming the pipeline runs
correctly before it is scaled to the full corpus. The goal is plumbing
validation — establishing that text flows correctly from corpus chunks through
two retrievers into a fused ranking — not measurement of retrieval quality,
which is impossible at this scale (single chapter, n = 10, no labelled
relevance judgments).

## 2. Design decisions

| Decision | Choice | Alternative considered | Rationale |
|---|---|---|---|
| Retrieval architecture | BM25 + French dense, fused | Dense-only | Directly instantiates H1: a lexical retriever (exact French terms) and a semantic retriever (paraphrase/meaning) catch different relevant chunks; the baseline must contain both to test the hypothesis. |
| Score combination | Reciprocal Rank Fusion (RRF) | Weighted score averaging | BM25 scores are unbounded and corpus-dependent; cosine similarities lie in [−1, 1]. Averaging compares incomparable scales. RRF fuses *ranks*, sidestepping the scale mismatch. |
| French tokenization (BM25) | spaCy `fr_core_news_sm`; drop multi-character stopwords; **keep single-character tokens**; fold accents; no lemmatization | Whitespace split; drop all stopwords | spaCy flags "a" (the verb *avoir*) as a stopword, but in this corpus "a" is a math variable ("a = kb"). Dropping it would remove central variables; the single-character rule preserves them. Accent folding ("théorème" → "theoreme") makes accent-free student queries match. Lemmatization is withheld as an ablation lever. |
| Dense embedding model | `intfloat/multilingual-e5-small` (smoke); model-agnostic interface | French-native model (e.g. Solon), e5-large | A small model proves the plumbing identically to a large one but downloads in a fraction of the time. The interface takes model id + prefix convention as parameters, so the production French model is a one-line change. Model selection for the full corpus is deferred and will be benchmarked. |
| Index content | Chunk text only | Text + heading/topic metadata | Baseline choice; enriching the index with structural metadata is a deliberate future lever, kept out of the baseline for clarity. |
| Subset selection | Deterministic coverage sample across content types | Random sample | A plumbing test needs known, explainable coverage (theory, theorem, definition, example, solution, proof, plus one figure-dropped edge case), not the uncontrolled distribution a random draw gives. |

## 3. Method

### 3.1 Corpus subset
Ten chunks were drawn deterministically (sorted by `chunk_id`, not random) from
the 84-chunk v1 corpus: 2 `definition`, 2 `theorem`, 1 `theory`, 2 `example`,
1 `solution`, 1 `proof`, and 1 chunk flagged `has_dropped_figure` as a
deliberate edge case (an explicit override of the corpus rule that filters
figure-dropped chunks from evaluation sets by default). The subset is frozen to
disk so every retriever indexes an identical document set.

### 3.2 Lexical retrieval (BM25)
Each chunk's text is tokenized with the French tokenizer (§2) and indexed with
Okapi BM25 (`rank-bm25`, default parameters k1 = 1.5, b = 0.75, untuned). A
query is tokenized identically; documents are ranked by BM25 score, with ties
broken deterministically by `chunk_id`.

### 3.3 Dense retrieval
Each chunk is embedded with the sentence-transformer model under the E5
convention: passages prefixed with `"passage: "`, queries with `"query: "`,
embeddings L2-normalized so that cosine similarity equals a dot product.
Documents are ranked by cosine similarity to the query embedding (ties broken
by `chunk_id`).

### 3.4 Fusion
The two ranked lists are combined by Reciprocal Rank Fusion:

    rrf_score(d) = Σ_r  1 / (k + rank_r(d))

summed over retrievers r, where rank_r(d) is d's 1-based position in retriever
r's candidate list (omitted if d is absent), and k = 60 (the canonical
constant; RRF is insensitive to it, so it is not tuned). Each retriever
contributes its top 20 candidates; the fused top 5 are returned.

## 4. Smoke-test observation (illustrative, not measured)

For the query *« Quand dit-on qu'un entier b divise un entier relatif a ? »*,
the definition chunk ranked first overall. Two component ranks illustrate the
complementarity that motivates H1:

- The **definition** chunk was ranked 1st by the dense retriever but only 3rd
  by BM25 — the semantic retriever recognised it as the answer.
- An **example** chunk was ranked 1st by BM25 (high lexical overlap) but 6th by
  the dense retriever, which correctly judged it less relevant; fusion demoted
  it accordingly.

This is qualitative evidence that the two retrievers surface different chunks
and that fusion blends them — consistent with H1's premise. It is not evidence
for H1, which requires labelled relevance judgments over a representative
corpus.

## 5. Prompt ablation: instruction strictness controls source-faithfulness

A follow-up probe tested whether the generator's tendency to override the
retrieved context could be controlled by the system prompt. A single controlled
item was used: CIAM chunk 0005 ("Si b divise a, alors |b| ≤ |a|") was corrupted
by flipping the inequality to the false |b| ≥ |a| and supplied as the sole
context for the question "que peut-on dire de la comparaison entre |b| et |a| ?".
The same item was run under three system prompts of increasing strictness:
(V1) the baseline "answer only from the extracts" prompt; (V2) a
strict-faithfulness prompt instructing the model to report the extract verbatim
even if it appears incorrect, while permitting a *separate* note flagging a
suspected error; and (V3) a hard prompt forbidding any correction, commentary,
or added content.

The result was monotonic. Under V1 the model overrode the corrupted extract,
answered with the mathematically correct |b| ≤ |a| from its own knowledge, and
mis-attributed that claim to the extract (a citation-faithfulness failure);
across repeated runs its behaviour was inconsistent, sometimes flagging the
discrepancy and sometimes not. Under V2 the model reported the extract
faithfully (|b| ≥ |a|), cited it correctly, and raised the suspected error in a
separate note recommending human verification. Under V3 it reported the extract
verbatim with no commentary. This indicates that, for this frontier model
(claude-sonnet-4-6), source-faithfulness is materially governed by prompt
design rather than being fixed model behaviour, and that a strict-faithfulness
prompt with an explicit error-flagging channel (V2) achieves both curriculum
fidelity and transparent surfacing of suspected OCR/source errors for human
adjudication. The V2 prompt was consequently adopted as the system's canonical
prompt (`src/generation/prompts.py`).

This is a single-item, few-run probe, not a quantitative result: behaviour was
stochastic under V1, and the test has not been repeated across multiple
corrupted facts or on a smaller language model. A systematic faithfulness
evaluation (multiple injected errors × repeated trials × model sizes) is
required before drawing conclusions, and connects directly to H3 (what the
LLM-as-judge must verify) and H4 (frontier vs. SLM grounding behaviour).

## 6. Limitations

- **Single chapter, n = 10.** No generalizable claim about retrieval quality
  can be made; observations are illustrative of mechanics only.
- **Placeholder embedding model.** `e5-small` was chosen for download speed,
  not French-math quality; the production model is unselected.
- **Untuned BM25.** Library-default parameters; no parameter search.
- **No relevance judgments.** Recall, MRR, nDCG, etc. cannot be computed; the
  check was a manual eyeball inspection.
- **Compressed score range.** At n = 10 with k = 60, RRF scores are nearly
  identical across the top results; rank order should not be over-read.
- **Grounding tested on a single item.** Generation and the grounding-injection
  check were run (§5), but on one corrupted fact under three prompts; source-
  faithfulness is not yet measured systematically (multiple injected errors ×
  repeated runs × model sizes).

## 7. Reproducibility

    uv run pytest src/retrieval/ src/generation/ -q
    uv run python "experiments/2026-06-01-baseline-smoke-test/select_chunks.py"
    uv run python "experiments/2026-06-01-baseline-smoke-test/run_retrieval.py"
    # generation steps require ANTHROPIC_API_KEY in the environment:
    uv run python "experiments/2026-06-01-baseline-smoke-test/run_pipeline.py"
    uv run python "experiments/2026-06-01-baseline-smoke-test/prompt_ablation.py"

Selection is deterministic; BM25 and dense inference are deterministic given a
fixed model. Random seed fixed to 42 per repository convention. LLM generation
is stochastic and is not expected to reproduce verbatim.
