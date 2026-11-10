# OCR validation for the Tutorly corpus: marker on CIAM Terminale C

**Date:** 2026-05-12
**Scope:** Chapter 2 ("Divisibilité dans Z") of the CIAM Terminale C textbook.
**Pipeline component:** `src/ocr/validation/` (commit hash to be filled in at PR time).
**Sample size:** 408 LaTeX equations, ~15 200 characters of prose (ground truth).

---

## 1. Motivation

The Tutorly RAG system retrieves curriculum-grounded chunks from Ivorian
Terminale C textbooks and BAC papers to answer student questions. The
corpus is constructed by OCR'ing scanned PDFs with [marker][marker],
producing markdown with embedded LaTeX. Two questions need answering
before that corpus can be trusted:

1. **Is the prose accurate enough that a BM25 / dense retriever can
   match a student's query against the right textbook passage?** A high
   prose character error rate would shift token spellings (e.g.
   *diviseur* → *divsieur*) and silently degrade retrieval.
2. **Are the equations preserved well enough that the LLM, once a chunk
   is retrieved, sees the correct mathematics?** A missing or corrupted
   equation in a theorem chunk renders the chunk useless for
   instructional grounding (H2) and harmful for generation (H4).

These two failure modes have different costs and require different
metrics. This document defines and reports both.

[marker]: https://github.com/VikParuchuri/marker

## 2. Data

| Artifact | Path | Content |
|---|---|---|
| Source PDF | `data/raw/` (gitignored) | Single chapter of the CIAM Terminale C textbook, ~20 scanned pages. |
| Marker output | `draft_codes/ocr_validation_results/content/output_md/extract_ciam_tc/extract_ciam_tc.md` | Markdown emitted by marker, with embedded LaTeX. |
| Ground truth (full) | `.../content/output_md/ground_truth_extract_ciam_tc.md` | Manually corrected version of the marker output, with the exercise section restored. |
| Ground truth (scope-matched) | `.../content/output_md/wo-exercises_ground_truth_extract_ciam_tc.md` | Same as above with the exercise section stripped, to match the scope marker actually covered. |

The comparison reported here uses the **scope-matched** ground truth so
that detection misses and hallucinations reflect OCR quality rather
than coverage choices made by marker.

## 3. Methodology

Each document is split into two streams — *prose* and *equations* —
which are evaluated independently.

### 3.1 Document split

LaTeX equations are extracted with a single regular expression that
prefers block delimiters over inline delimiters:

```python
EQ_REGEX = re.compile(r"\$\$(.+?)\$\$|\$([^\$\n]+?)\$", re.DOTALL)
```

The alternation matches `$$...$$` first; only if that fails does the
engine try `$...$`. The inline arm forbids `$` and newlines so it
cannot straddle a block boundary or a paragraph break. This avoids the
"double counting" pitfall in which `$$xy$$` is interpreted both as a
block equation containing `xy` and, on a second pass, as two inline
equations containing `x` and `y` — see §5 for the consequence on a
naive implementation.

In the CIAM Chapter 2 ground truth the split yields **14 block** and
**394 inline** equations (408 total).

### 3.2 Prose metrics

Define the **prose** of a document as the text remaining after
equations and markdown markup are removed. Markdown stripping covers
heading markers (`#+`), list bullets (ASCII `-`, `*` and Unicode `•`),
bold wrappers (`**…**`), inline code (`` `…` ``), image links
(`![…](…)`), and inline HTML. Whitespace is then collapsed.

We report two standard OCR metrics on the resulting prose pair:

- **Character Error Rate (CER).** Let $g$ be the ground-truth prose
  and $p$ the predicted prose. Let $S$, $D$, $I$ be the number of
  character substitutions, deletions, and insertions in the
  minimum-edit alignment of $p$ against $g$. Then
  $$
  \mathrm{CER}(g, p) \;=\; \frac{S + D + I}{|g|}.
  $$
- **Word Error Rate (WER).** The same formula on whitespace-tokenized
  word sequences instead of characters. WER is the more
  retrieval-relevant of the two because BM25 operates on word-like
  tokens.

Both are computed via `jiwer.cer` and `jiwer.wer`.

### 3.3 Equation detection

Treating each equation as a discrete object to be detected, we compute
the standard retrieval triple:
$$
P \;=\; \frac{|M|}{|E_p|},\qquad
R \;=\; \frac{|M|}{|E_g|},\qquad
F_1 \;=\; \frac{2 P R}{P + R},
$$
where $E_g$ and $E_p$ are the equation lists from the two documents
and $M \subseteq E_g \times E_p$ is the set of aligned pairs (defined
in §3.4).

### 3.4 Equation alignment

Index-based pairing ($g_i$ against $p_i$) is fragile: one missed
equation desynchronises every subsequent comparison and the error rate
collapses to noise. Instead, we align the two equation lists with a
Needleman–Wunsch sequence alignment.

Each equation is first reduced to a **canonical form** via
`normalize_latex`:
1. Apply LaTeX synonym substitutions (described in §3.5).
2. Remove all whitespace.

Let $\sigma$ denote canonicalisation. Define the **normalized
Levenshtein similarity** between two strings:
$$
s(a, b) \;=\; 1 \;-\; \frac{d_L(a, b)}{\max(|a|, |b|)}
\;\in\; [0, 1],
$$
where $d_L$ is the Levenshtein edit distance.

We then fill a dynamic-programming table $C \in \mathbb{R}^{(n+1)\times(m+1)}$
with $n = |E_g|$, $m = |E_p|$, and
$$
C_{i,j} \;=\; \min\!\Bigl\{
  \underbrace{C_{i-1,j-1} + \bigl(1 - s(\sigma(g_i), \sigma(p_j))\bigr)}_{\text{pair } g_i \text{ with } p_j},\;
  \underbrace{C_{i-1,j} + \gamma}_{g_i \text{ unmatched}},\;
  \underbrace{C_{i,j-1} + \gamma}_{p_j \text{ unmatched}}
\Bigr\},
$$
with boundary conditions $C_{i,0} = i\gamma$, $C_{0,j} = j\gamma$, and
gap penalty $\gamma = 0.5$. The minimising operation at each cell is
recorded so the alignment can be recovered by backtracking from
$C_{n,m}$.

The output is a triple $(M, U_g, U_p)$ where $M$ is the list of
matched index pairs (with their similarities), $U_g$ are
ground-truth-only indices ("missing"), and $U_p$ are
prediction-only indices ("hallucinated").

Pairs with $s < \tau$ (we use $\tau = 0.3$) are demoted post-hoc to
($U_g$, $U_p$): if the aligner could only pair two equations with
near-zero similarity, treating them as a paired error overstates
recall and understates the missing / hallucinated counts.

The choice $\gamma = 0.5$ ensures that two equations are preferred to
match only when their similarity exceeds the cost of opening a pair
of gaps; this keeps the aligner from inventing spurious pairings
across distant regions of the document.

### 3.5 LaTeX synonym normalisation

A conservative set of substitutions collapses well-known LaTeX
synonyms before similarity is computed:

| GT form | Prediction form | Justification |
|---|---|---|
| `\leq` | `\le` | Identical rendering. |
| `\geq` | `\ge` | Identical rendering. |
| `\neq` | `\ne` | Identical rendering. |
| `\rightarrow` | `\to` | Identical rendering. |
| `\overrightarrow{X}` | `\vec{X}` | Both produce an arrow over the argument. French math conventions prefer `\overrightarrow`; marker tends to emit the latter. |

We deliberately do **not** normalise the following, despite
superficial similarity:

- `(\Delta)` vs `\Delta` — in French geometry $(\Delta)$ denotes
  *the line labelled $\Delta$*, whereas the bare letter denotes the
  letter itself. Dropping the parentheses is a real loss of
  information.
- `\equiv` vs `=` — these mean different things in modular
  arithmetic: $a \equiv b \pmod n$ is not the same statement as
  $a = b$.
- `\Delta` vs `\Lambda` — visually similar Greek letters but
  semantically distinct.

Aggressive normalisation would mask the OCR errors we care most about
detecting. The principle followed is: *normalise only differences
that the LLM consuming the chunk would treat as semantically
equivalent.*

### 3.6 Equation accuracy on matched pairs

Conditional on detection, the quality of a recovered equation is
summarised by the distribution of similarities over $M$:

- $\mathrm{ExactMatch} = \frac{1}{|M|}\sum_{(i,j) \in M} \mathbf{1}[s_{ij} = 1]$
- $\mathrm{HighSim} = \frac{1}{|M|}\sum_{(i,j) \in M} \mathbf{1}[s_{ij} \geq 0.95]$
- Mean, median, P25, P75 of $\{s_{ij}\}$.

The 0.95 threshold corresponds to "off by at most a few characters in
an equation of length 20–40", which our manual inspection finds
acceptable for retrieval — the BM25 index will still rank the chunk
similarly, and an LLM consuming the chunk recovers the intended
expression.

## 4. Results

### 4.1 Prose

| Metric | Value |
|---|---|
| Characters (GT)            | 15 146 |
| Characters (prediction)    | 16 833 |
| **CER**                    | **11.51 %** |
| **WER**                    | **14.40 %** |

The prediction is ~11 % longer than the ground truth, driven by
marker re-injecting page-break artefacts and image references that
the manual transcription removed.

### 4.2 Equation detection

| Metric | Value |
|---|---|
| Ground-truth equations | 408 |
| Predicted equations    | 361 |
| Matched                | 335 |
| Missing (recall miss)  | 73 |
| Hallucinated (precision miss) | 26 |
| **Precision**          | **92.80 %** |
| **Recall**             | **82.11 %** |
| **F1**                 | **87.13 %** |

Recall is the limiting factor: marker fails to detect roughly one in
five equations from the source, primarily short single-symbol
equations embedded in inline French prose (e.g. references to a line
$(\Delta')$ or a point $M_1$ inside a paragraph). Hallucinations are
rarer and, on inspection, mostly correspond to genuine equations
belonging to scope outside the comparison — see §6.

### 4.3 Equation accuracy on matched pairs

| Metric | Value |
|---|---|
| Exact-match rate         | 87.46 % |
| $\geq 0.95$ similarity   | 89.55 % |
| Mean similarity          | 0.9733 |
| Median similarity        | 1.0000 |
| P25 / P75 similarity     | 1.0 / 1.0 |

The distribution is heavily concentrated at $s = 1$ with a long tail
of low-similarity errors. The interquartile range is degenerate
because more than 75 % of matched equations are exact matches; the
remaining error mass is concentrated below the P25 cutoff.

### 4.4 Error taxonomy from worst-case inspection

Sorting matched pairs by ascending similarity surfaces marker's
systematic failure modes. The five categories below cover the
twenty worst-matched pairs.

**Greek letter confusion** — visually similar letters substituted:
```
GT:   t \circ r = s_{\Delta'} \circ s_{\Delta}
PRED: t \circ r = s_{\Lambda} \cdot \circ s_{\Lambda}
```

**Layout artefacts absorbed into equations** — markdown bullets and
neighbouring French connectives bleed into the equation token:
```
GT:    A = A'
PRED:  -Si\ A = A'
```
```
GT:    - 81 \equiv 0 [9]
PRED:  \bullet - 81 \equiv 0 [9]
```

**Decorations lost** — accents, hats, and other diacritics dropped:
```
GT:   2\widehat{(\vec{v}, \vec{w})} = \hat{\alpha}
PRED: 2(\vec{v}, \vec{w}) = \hat{\alpha}
```

**Parenthetical labels stripped** — semantic loss specific to French
geometry conventions:
```
GT:    (\Delta')
PRED:  \Delta
```

**Spurious additions** — extra symbols introduced around legitimate
expressions:
```
GT:    (\mathfrak{D})
PRED:  \mathcal{L}(\mathfrak{D})
```

## 5. Iteration: what the first implementation got wrong

The initial validation notebook (preserved in commit history)
produced a CER of 27.7 % and an "equation structural accuracy" of
13.8 %. Three independent defects made these numbers uninterpretable.

**Wrong input files.** The notebook compared two *ground-truth*
files against each other — the full GT and the wo-exercises GT —
rather than comparing the marker output against either. The 27 %
CER measured the byte-level size of the exercise section, not OCR
quality. This is the dominant explanation for the original numbers.

**Index-based equation pairing.** Equations were compared positionally:
$g_i$ against $p_i$. Marker's first detection failure
desynchronised the lists, and every subsequent comparison was
between unrelated equations. With 436 versus 547 equation counts
(the raw inflation discussed below), the index-based pairing
collapsed to near-zero similarity past the first divergence.

**Double-counted inline equations.** The notebook ran two
independent regular expressions — `\$\$(.*?)\$\$` and
`\$(.*?)\$` — over the same text. The inline pass re-matched the
contents of block equations a second time, inflating the count of
detected equations by 25–35 %. This was the source of the 436 vs.
547 mismatch.

Correcting these three defects, plus adding LaTeX synonym
normalisation and a Unicode-bullet stripper, yields the numbers in
§4. The headline movements relative to the broken baseline were:

| | Original | Corrected | Δ |
|---|---|---|---|
| Prose CER     | 27.72 % | 11.51 % | −16.21 pp |
| Equation F1   | n/a *   | 87.13 % | — |
| Equation exact-match | 13.82 % * | 87.46 % | +73.64 pp |

\* The original "Equation Structural Accuracy" is not directly
comparable to either of the corrected metrics; it was an average of
position-aligned similarities over a misaligned pairing.

A specific guard against the inline-double-count regression is now
included in the test suite
(`test_block_is_not_double_counted_as_two_inlines`).

## 6. Limitations

**Single-chapter scope.** The reported numbers reflect Chapter 2 of
one textbook. Marker performance plausibly varies across content
types (definitions, theorems, worked examples, exercise statements
with numbered enumeration) and across scan quality. Multi-chapter
validation is the natural next step.

**Imperfect scope matching.** The wo-exercises ground truth strips
the exercise section from the manual transcription, but a small
number of marker-emitted equations belong to exercise content that
was not perfectly trimmed (notably a long `\begin{array}` block and
several isolated equation fragments). These contribute to the
hallucination count and modestly understate marker's precision.

**No content-type stratification.** The metrics aggregate over the
entire prose / equation streams. A 5 % error rate inside a theorem
statement is far more damaging to downstream retrieval than the
same rate in a transitional sentence. Once the corpus chunker is
in place (planned for Week 2), the same harness should be re-run
with per-chunk and per–`content_type` breakdowns to expose where
errors concentrate.

**LLM-as-judge agreement not measured.** The similarity metric
treats LaTeX as a string. Two equations with $s = 0.9$ might be
semantically identical (a single brace difference) or semantically
distinct (an off-by-one exponent). A small LLM-as-judge pass over a
sample of matched pairs would calibrate the relationship between
edit-distance similarity and mathematical equivalence, and is
planned as part of H3.

## 7. Implications for retrieval

The three measured quantities map directly onto downstream
retrieval failure modes:

- An 11.5 % prose CER means roughly one character in nine is wrong
  in the BM25 token stream. French has long, morphologically dense
  vocabulary (*divisibilité*, *congruence*, *réciproquement*); a
  one-character error per word is enough to defeat exact-term
  matching for ~15 % of tokens. Dense retrieval is more robust to
  this but is not immune, and the present corpus is small enough
  that any retrieval-quality gap matters.
- An 18 % equation-recall miss means almost one in five equations
  is entirely absent from the index. Mathematical content cannot
  be retrieved by paraphrase; if the equation is missing, the
  chunk loses its citable evidence.
- An 87 % exact-match rate on detected equations means that, when
  a chunk *is* retrieved, the LLM sees a faithful equation about
  seven times out of eight. The remaining one-in-eight has
  characteristic, predictable error modes (Greek letter
  confusion, layout absorption) which would benefit from a
  targeted post-OCR cleanup pass.

The corpus is therefore usable for the H1 (hybrid retrieval) and
H2 (instructional retrieval) experiments, provided the eventual
ablation reports break out the contribution of OCR error to any
end-to-end retrieval gap.

## 8. Reproducibility

```bash
python -m src.ocr.validation.compare \
  --gt   draft_codes/ocr_validation_results/content/output_md/wo-exercises_ground_truth_extract_ciam_tc.md \
  --pred draft_codes/ocr_validation_results/content/output_md/extract_ciam_tc/extract_ciam_tc.md \
  --out  experiments/2026-05-12-marker-validation-ciam-tc/results.json
```

The script writes a deterministic JSON report containing every
number quoted in §4 plus the twenty lowest-similarity matched pairs
and the first twenty unmatched equations on each side. Unit tests
for the metric primitives live in
`src/ocr/validation/test_metrics.py` (14 tests, including
regressions against the three §5 defects).
