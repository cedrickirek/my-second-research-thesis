## M9. All metrics and threats to validity

### M9.1 Statistical methods

**Retrieval metrics**. Each query is scored against the human qrels at cutoffs $k \in \{5, 10\}$. A chunk counts as relevant when its grade is ≥ 2, and a chunk that no annotator judged counts as 0. The pedagogical retriever returns exactly five chunks, so H2 is compared at $k = 5$ only. Queries with no chunks graded 2 or higher have recall and nDCG undefined and are left out of the averages for those two metrics. 

- **Recall@k**: the share of the query's relevant chunks that appear in the top $k$. 
- **nDCG@k** (normalised discounted cumulative gain): uses the full 0–3 grade. Each retrieved chunk earns a gain of $2^{g}-1$ (0, 1, 3 or 7 points), divided by $\log_2(\text{rank}+1)$ so that lower ranks count less. The total is divided by the total of the best possible ordering of the query's judged chunks, which gives a score between 0 and 1.
- **MRR** (mean reciprocal rank): $1/\text{rank}$ of the first relevant chunk (0 if none is retrieved), averaged over queries.

**Agreement coefficients**. Both compare the agreement observed with the agreement expected by chance: the highest is 1 = perfect agreement.

- **Krippendorff's α** (ordinal): $\alpha = 1 - D_o/D_e$, the observed disagreement over the disagreement expected by chance. It accepts any number of raters and missing grades, which suits the anchor design (ten raters, a different pair of raters on each query). Because it is ordinal, a 0 vs 3 disagreement weighs more than a 1 vs 2. Used for the human ceiling on the 155 double-rated anchor pairs, for the assessor against the humans, and for the assessor's test–retest reliability across its two runs.
- **Cohen's κ**: for exactly two raters, $\kappa = (p_o - p_e)/(1 - p_e)$, with $p_o$ the observed and $p_e$ the chance agreement. Reported in two forms: quadratic-weighted on the 0–3 scale (a disagreement of $d$ grades weighs $d^2/9$), and unweighted on the binary relevant/non-relevant split at grade 2.

**Significance and robustness (H1 and the H2 retrieval side)**.

- **Paired query-level bootstrap** (B = 2,000, seed 42): (Efron & Tibshirani 1993; for IR metrics, Sakai 2006) the 100 queries are resampled with replacement, both retrievers are scored on the same resampled set in each replicate, and the per-replicate difference yields a 95% percentile confidence interval and the share of replicates in which the difference is positive. This is a resampling interval for a fixed query set, not a parametric p-value.
- **Label-perturbation sensitivity**: the H1 (k = 5, k = 10) and H2 (k = 5) differences are recomputed on fifteen perturbed versions of the labels: a relevance cut at 1 or 3 instead of 2; severity recalibration, where each rater's grades are shifted so their mean matches the panel's; anchor pairs resolved by the higher or the lower of the two grades instead of their rounded mean; and each of the ten annotators left out in turn.

**Ranking agreement (H3 primary test)**. The four retrievers are ordered by nDCG@5 under the LLM qrels and under the human qrels, and the two orderings are compared by:

- **Exact ordering agreement**: whether all four retrievers come out in the same order.
- **Pairwise concordance**: the share of the six retriever pairs that both rankings put in the same order.
- **Kendall's τ:** $\tau = (C - D)/6$, with $C$ the concordant and $D$ the discordant pairs. It runs from −1 (reversed) to +1 (identical). It is coarse with only four systems, because a single swap moves it by 0.33.

> Table M1. Summary of the measures in §M9.1. $g_i$ = grade of the chunk at rank $i$; $N$ = number of
> queries; $D_o$, $D_e$ = observed and chance-expected disagreement; $o_{ij}$, $e_{ij}$ = observed and
> chance-expected counts of the grade pair $(i, j)$; $p_o$, $p_e$ = observed and chance agreement;
> $C$, $D$ = concordant and discordant retriever pairs.
>
> | Measure                        | Formula                                                                 | In brief                                                                                   |
> |--------------------------------|-------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
> | Recall@k                       | $\dfrac{\text{relevant chunks in top } k}{\text{relevant chunks for the query}}$ | Share of the relevant chunks (grade ≥ 2) that are retrieved. H1, H2.                       |
> | nDCG@k                         | $\dfrac{\text{DCG@}k}{\text{ideal DCG@}k}$, $\text{DCG@}k = \sum_{i=1}^{k} \dfrac{2^{g_i}-1}{\log_2(i+1)}$ | Graded quality of the top $k$, rewarding high grades near the top; 0 to 1. H1, H2, H3 ranking. |
> | MRR                            | $\dfrac{1}{N}\sum_{q} \dfrac{1}{\text{rank of first relevant chunk}}$   | How early the first relevant chunk appears. H1, H2.                                        |
> | Krippendorff's α (ordinal)     | $1 - D_o / D_e$                                                         | Agreement beyond chance; any number of raters, missing grades allowed. Human ceiling, assessor vs humans, test–retest. |
> | Cohen's κ, quadratic-weighted  | $1 - \dfrac{\sum_{ij} w_{ij}\, o_{ij}}{\sum_{ij} w_{ij}\, e_{ij}}$, $w_{ij} = (i-j)^2/9$ | Two-rater agreement on the 0–3 scale; distant grades weigh more. Pilot, two-rater summary.  |
> | Cohen's κ, binary              | $\dfrac{p_o - p_e}{1 - p_e}$                                            | Two-rater agreement on relevant vs not relevant (grade ≥ 2). Assessor vs humans at the 1↔2 boundary. |
> | Exact ordering agreement       | 1 if both orderings are identical, 0 otherwise                          | Do LLM and human qrels rank the four retrievers the same way? H3.                          |
> | Pairwise concordance           | $C / 6$                                                                 | Share of the six retriever pairs ordered alike. H3.                                        |
> | Kendall's τ                    | $(C - D) / 6$                                                           | Ranking similarity, from −1 (reversed) to +1 (identical). H3.                              |

### M9.2 Threats to validity

- OCR quality: the OCR error rate (prose CER 11.51%, equation exact-match 87.46%; Annex E) was measured on a single hand-transcribed chapter using marker's plain mode, while the indexed corpus was produced with its LLM/vision mode. The quality of the indexed text is therefore assumed from that chapter, not measured. Every retrieval result rests on this text.
- Gold provenance: the coverage qrels (90% of all qrels) are single-rater, and 8 of the 10 raters are former or current Terminale C students rather than teachers. Where two raters graded the same pair, they agreed only moderately (ordinal α = 0.46 on the 155 anchor pairs, §4.1.1). The label-perturbation analysis (§M9.1) shows that the H1 and H2 verdicts hold in all 16 label scenarios
- Assessor circularity and paraphrase sensitivity: LLM labels may tilt toward the dense channel,
  contained because the retrieval verdicts conclude from human qrels, never LLM qrels; the single
  locked prompt makes paraphrase sensitivity a recorded limitation.
- Contamination and leakage: BAC 2025 is held out to limit leakage, but part of the measured H1
  effect may be attributable to lexical overlap from the synthesised-query construction, and the
  held-out slice (n = 9) is too small to settle external validity. Worked-example contamination is
  ≈ 32% of the `theory`-labelled chunks (95% CI 20–48%, n = 40), about 12% of the theory bucket; a full-corpus estimate is future work.
- Corpus and scope: figure-dropping (15.7% of chunks) and geometry exclusion bind every claim to
  non-geometry, text-only Terminale C content.
- Statistical power: 100 queries, four retrievers, and a 155-pair anchor overlap limit
  statistical power and generality.
