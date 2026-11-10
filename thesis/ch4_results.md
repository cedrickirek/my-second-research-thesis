# Chapter 4. Results

This chapter presents the empirical results for the three hypotheses executed within the time and
data available: H1, the H2 retrieval side, and the reframed H3. It is organised so the evidence is
read in the order in which it is trusted: first the human inter-annotator agreement that bounds
how far the gold labels can be relied upon (§4.1), then the two retrieval comparisons those labels
adjudicate (§4.2, §4.3), then a consolidated view of all four retrievers (§4.4), then the
validation of the LLM relevance-assessor the same labels make possible (§4.5), and finally what is
not a result here (§4.6).

Two reading conventions apply throughout. First, retrieval differences are reported as a point
estimate Δ with its 95% paired-bootstrap CI in brackets and the bootstrap probability
P(Δ>0) that the difference carries its hypothesised sign; an interval excluding zero is read as
unlikely to be an artefact of the fixed 100-query set, and every verdict is additionally
stress-tested under the label-perturbation analysis of §4.4.2. Second, the H1 and H2 retrieval
verdicts are computed against the human-panel qrels, never the LLM qrels — the LLM qrels exist
only to test the assessor in §4.5.

## 4.1 Reliability of the gold labels

The retrieval comparisons are only as trustworthy as the relevance labels they are scored against,
and the reframed-H3 ceiling of §4.5 is that human agreement. This section reports the
inter-annotator agreement that bounds how far the labels can be trusted (§4.1.1), then the dataset
profile and quality-control checks on the labels themselves (§4.1.2).

### 4.1.1 Inter-annotator agreement

Agreement is computed over the anchor overlap of the disp10 design — the subset of (query, chunk)
pairs labelled by more than one annotator. Two properties of the panel bear on how the number is
read: it is a mixed-expertise ceiling (agreement across the two teachers and eight students,
not a pure-expert standard), and the coverage qrels behind H1/H2 are mostly student-produced
single-rater labels.

> Table 1. Human inter-annotator agreement on the disp10 anchor overlap. Ordinal Krippendorff's α
> (0–3 scale) is the primary statistic; nominal α and the two-rater summary are reported alongside.
>
> | Statistic                              | Value      |
> |----------------------------------------|------------|
> | Krippendorff's α — ordinal (0–3)       | 0.46       |
> | Krippendorff's α — nominal             | 0.16       |
> | Units (total / multi-rated)            | 1,565 / 155 |
> | Annotators                             | 10         |
> | Two-rater exact agreement              | 38.7%      |
> | Two-rater adjacent agreement (±1)      | 87.7%      |
> | Two-rater weighted κ                   | 0.47       |

The ordinal α is the headline because relevance is an ordered 0–3 judgement: an off-by-one
disagreement (a 2 vs. a 3) is less severe than a polar one (a 0 vs. a 3), and the ordinal weighting
encodes exactly that. The ordinal α of 0.46 is a moderate mixed-panel ceiling, and the
comparison of exact (38.7%) to adjacent (87.7%) agreement shows why it is not higher: only one
co-rating in eight (12.3%) is a disagreement of more than one grade, so the bulk of the residual
divergence is threshold noise around the soft 1↔2 cut — the boundary between "not used by a
correct solution" and "used" — rather than substantive disagreement about whether a chunk is
on-topic. The large gap between the ordinal α (0.46) and the nominal α (0.16) is the same fact from
the other side: treated as unordered categories the labels look weak, but the disagreements are
overwhelmingly near-misses on an ordered scale, which the nominal coefficient cannot see. This
moderate-but-orderly agreement is what licenses reading the H1/H2 differences as point estimates
against a noisy gold, and is exactly why each is additionally given a bootstrap interval.

By the Landis and Koch (1977) benchmark, 0.46 is "moderate" (0.41–0.60) — below the thresholds
conventional for content analysis, but those presume a single true category, which graded relevance
is not. The relevance-assessment literature treats moderate overlap as the expected operating
condition: Voorhees (2000) found that substantially different relevance-judgment sets still induced
highly stable system rankings, and Bailey et al. (2008) found that mixed expert/non-expert panels
agree less yet remain usable for ranking systems. A two-teacher, eight-student panel is therefore
expected to land at a moderate ceiling — the leave-one-out spread of 0.34–0.59 (§4.4.2) confirms
this is a property of the whole panel, not one weak rater — which is exactly why the H3 validation
leads with ranking agreement and treats per-item α as secondary. Fuller interpretation is
deferred to Chapter 5.

### 4.1.2 Annotation dataset properties and quality control

Because the retrieval verdicts are scored against these labels, the labels themselves are profiled
and quality-controlled before any metric is read. Three properties matter.

Relevance base-rate and rater severity. Across all 1,720 labels the grade distribution is
skewed low (0: 30.5%, 1: 32.3%, 2: 24.9%, 3: 12.3%; mean 1.19, 37.2% relevant at the ≥ 2 cut) — the
direct cause of the low nominal α. More consequential is severity heterogeneity: per-annotator
mean grade ranges from 0.80 to 1.69, a better-than-twofold spread in how readily a rater calls a
chunk relevant. Two raters are markedly lenient (mean 1.69, 1.68), two markedly severe (0.80, 0.89),
one defaults heavily to grade 1, and one uses the scale near-bimodally. This is the heterogeneity
the sensitivity analysis (§4.4.2) is designed to absorb, reported here rather than hidden.

Relevance by content type — bearing on H2. Relevance is essentially flat across chunk content
types: worked examples (mean 1.20) and solutions (1.18) are judged about as relevant as theory
(1.24) or theorems (1.27) — lower by ≤ 0.09 on the 0–3 scale, and no lower on the binary ≥ 2 cut
Recall uses (solutions are judged relevant 41.0% of the time, against theory's 40.3%). This matters
for §4.3: the pedagogical retriever's enforced example slots are not seating systematically
lower-relevance material, so any retrieval-side H2 deficit cannot be explained by examples being
judged irrelevant — it must come from displacing higher-ranked relevant chunks, a
near-relevance-neutral substitution. Consistently, the labelled pool precision of the pedagogical
retriever's returned chunks is the highest of the four variants (47.6% relevant, vs. 43.8%
hybrid, 39.5% BM25, 39.2% dense).

Coverage and integrity. The judged set covers all 100 queries with a median of 5 relevant chunks
per query (4 queries have no chunk judged relevant at ≥ 2 and are NaN-guarded out of the per-query
means). A structural quality-control pass found no integrity faults — no duplicate pairs, no
labels outside the dispatched set, no query/chunk-id inconsistency, no out-of-range grades — and
no evidence of end-to-end file misalignment: each rater's mean absolute disagreement with its
anchor partners is within the panel norm (largest deviation z = +0.55 against a flag threshold of
1.5), and grade-entropy and longest-run checks show no straight-lining. A single localised
likely-error (one severe rater inverted its grades on one differential-equation query) was left
uncorrected, because post-hoc editing of labels to raise agreement would compromise the gold, and
§4.4.2 shows no single label or rater drives the verdicts. The labels are sound and are used in full.

## 4.2 H1 — hybrid vs. dense retrieval

H1 is the hypothesis that the RRF hybrid outperforms dense-only retrieval on the 100-query set,
scored against the human-panel qrels v1.0. The registered primary metric is nDCG@5; Recall@5 and
MRR are reported alongside, with the k = 10 comparison in §4.4.

> Table 2. H1: hybrid (RRF) vs. dense-only on the 100-query set, human-panel qrels v1.0. The last
> two rows split nDCG@5 by query source (synthesised / held-out BAC-2025).
>
> | Metric               | Dense | Hybrid (RRF) | Δ (Hyb − Dense)            | P(Δ>0) |
> |----------------------|-------|--------------|----------------------------|--------|
> | Recall@5             | 0.373 | 0.411        | +0.038 [−0.009, +0.085]    | 0.95   |
> | nDCG@5 (primary) | 0.476 | 0.525        | +0.049 [+0.009, +0.093]| 0.99   |
> | MRR                  | 0.612 | 0.663        | +0.051 [−0.012, +0.115]    | 0.95   |
> | nDCG@5 (synth, n=91) | 0.476 | 0.540        | +0.064                     | —      |
> | nDCG@5 (BAC25, n=9)  | 0.472 | 0.381        | −0.091 [−0.315, +0.097]    | 0.21   |

Three secondary analyses accompany the main contrast. Leakage control: the last two rows split
nDCG@5 over the 91 synthesised queries and the 9 held-out BAC-2025 queries; BAC 2025 is de-indexed
from the corpus, so a hybrid advantage surviving on that slice — where no source passage can leak —
would be evidence the H1 effect is not an artefact of train/test overlap (the n = 9 slice is read as
corroboration, not an independent test). Query-type stratification: the per-bucket hybrid
advantage in nDCG@5 is single-leçon +0.065 (n = 60), multi-notion +0.040 (n = 20),
hard-edge +0.015 (n = 20) — largest on the simplest single-topic queries and smallest on the
hard-edge ones, the opposite of the hypothesis that the sparse channel earns its place on rare-term
matches. Three-way channel comparison: the hybrid's nDCG@5 (0.525) exceeds both BM25 (0.489) and
dense (0.476) alone, so its gain is a genuine fusion benefit, not merely the better of the two
channels (full grid in §4.4).

Interpretation. H1 is supported, with one honest qualification about why it holds. On the
primary metric the hybrid beats dense by +0.049 nDCG@5, with a 95% bootstrap CI of [+0.009, +0.093]
that excludes zero; it is a genuine two-channel fusion, and it is robust to every annotator
scenario of §4.4.2 and to dropping any single rater. The qualification concerns the effect's
source. The advantage is carried by the sparse (BM25) channel, which behaves very differently
across query sources: on the 91 synthesised queries BM25 alone (0.498) outperforms dense (0.476),
whereas on the 9 held-out BAC-2025 queries BM25 (0.390) underperforms dense (0.472). The
synthesised queries also share more vocabulary with their relevant chunks than the real exam queries
do (55.5% vs. 45.6% query-term coverage), and the hybrid gain concentrates on precisely the queries
where that overlap is highest. Part of the measured H1 advantage is therefore attributable to
lexical overlap between the synthesised evaluation queries and the indexed corpus — a property of how
the evaluation set was built, not necessarily of how a student would phrase a question. This is
not read as a held-out reversal: the −0.091 on the BAC-2025 slice comes from two of nine queries
(one with a single relevant chunk, making its nDCG near-degenerate), and its CI [−0.315, +0.097] is
too wide to be informative — nine queries cannot settle the question. The honest verdict: H1 holds
on this corpus and is statistically supported on the primary metric, but leans on lexical matching
that the synthetic-query construction advantages; confirming the hybrid gain on real student queries
is the natural next test. The dense (semantic) channel is the one that holds up on the real
held-out questions and is the more conservative choice where query phrasing cannot be assumed to
track the corpus.

## 4.3 H2 (retrieval side) — pedagogical vs. hybrid retrieval

It must be stressed that nDCG@5 is neither necessary nor sufficient for the H2 pedagogical-quality
claim. The pedagogical retriever deliberately passes over higher-relevance theory chunks to seat
its two example slots, so it can lose on nDCG@5 and still tutor better, or win with no tutoring
gain. The retrieval-side contrast therefore tests one thing only: whether the enforced theory–example
mix is achieved without sacrificing relevance. The pedagogical-quality verdict itself is not
delivered in this thesis — it depends on the generation-side evaluation, which is future work (§4.6).

> Table 3. H2: pedagogical vs. hybrid at the matched cut-off k = 5. The "cond." row restricts to the
> 98 queries whose fused pool held ≥ 1 example-type chunk (no example-slot fallback).
>
> | Metric          | Hybrid | Pedagogical | Δ (Ped − Hyb)            | P(Δ>0) |
> |-----------------|--------|-------------|--------------------------|--------|
> | Recall@5        | 0.411  | 0.377       | −0.034 [−0.061, −0.007]  | 0.004  |
> | nDCG@5          | 0.525  | 0.504       | −0.022 [−0.043, +0.001]  | 0.03   |
> | MRR             | 0.663  | 0.627       | −0.035 [−0.080, +0.006]  | 0.05   |
> | nDCG@5 (cond.)  | ≈0.525 | ≈0.503      | −0.022 (n = 98)          | —      |

Two features shape how the numbers read. The marginal vs. conditional split: on example-poor
queries the fallback rule backfills the example slots with theory content, degenerating the
pedagogical retriever toward the hybrid baseline. The marginal row (all queries) is the realistic
operational estimate; the conditional row (no fallback) is the cleaner test of the principle. Here
the fallback fires on only 2 of 100 queries (example-availability 98%; mean 1.96 of 2 example
slots filled), so the two estimates are effectively identical (both −0.022 nDCG@5). And a
conservative bias from baseline contamination: a manual audit of `theory`-labelled chunks (n = 40,
seed 42) estimates that ≈ 32% are in fact headingless worked examples (95% CI 20–48%), about 12% of the theory bucket, so the
hybrid baseline can already surface example-like content through its theory channel and partially
close the gap the pedagogical retriever enforces by construction — meaning a positive H2 effect would
appear in spite of a baseline that captures some of the same intent.

Interpretation. The H2 necessary-condition is not met: the pedagogical retriever is, by a small
but consistent margin, below hybrid on relevance. At the matched k = 5 it trails hybrid by −0.034
Recall@5 (CI [−0.061, −0.007], excluding zero) and −0.022 nDCG@5; the result is stable across the
sensitivity scenarios (Recall@5 Δ in [−0.041, −0.026] throughout) and barely moves under
example-availability conditioning. Three facts keep this from being a refutation. First, the deficit
is small and arises despite the conservative baseline contamination above. Second, example and
solution chunks are judged as relevant as theory, and the pedagogical retriever's returned set has
the highest labelled pool precision of the four variants (47.6%); it is not seating low-relevance
material, it is making a near-relevance-neutral substitution that trades a little ranking relevance
for a guaranteed theory-plus-example structure. Third, and decisively, nDCG@5 is the wrong
instrument for the H2 claim: per-chunk relevance cannot reward the pairing of a theory chunk with
its worked example, which is the entire pedagogical hypothesis. The retrieval-side result therefore
establishes only that the enforced mix is achieved at a small, bounded relevance cost — a
necessary-conditions check, passed in the weak sense that the cost is small — and emphatically not
the pedagogical-quality verdict, which depends on the generation-side evaluation this thesis does not
execute. (The −0.30 figure a naïve k = 10 comparison would produce is an artefact of scoring a
fixed 5-chunk retriever against a 10-chunk one, and is not reported as a result.)

## 4.4 Consolidated retrieval results (all four variants)

For completeness, and to support the H1 three-way analysis and the H3 ranking validation, the full
metric grid for all four retrievers is reported in one place, then stress-tested against annotator
behaviour (§4.4.2).

### 4.4.1 The four-variant comparison

> Table 4. All four retrievers on the 100-query set, human-panel qrels v1.0. Best value per column
> in bold.
>
> | Variant        | Recall@5 | nDCG@5   | Recall@10 | nDCG@10  | MRR      |
> |----------------|----------|----------|-----------|----------|----------|
> | BM25           | 0.370    | 0.489    | 0.599     | 0.561    | 0.657    |
> | Dense          | 0.373    | 0.476    | 0.590     | 0.552    | 0.612    |
> | Hybrid (RRF)   | 0.411| 0.525| 0.678 | 0.613| 0.663    |
> | Pedagogical    | 0.377    | 0.504    | —†        | —†       | 0.627    |
>
> † The pedagogical retriever returns a fixed 5-chunk bundle, so its top-10 equals its top-5 and the
> k = 10 cells are undefined; H2 (§4.3) is therefore scored only at the matched k = 5.

The ranking the four variants induce is itself a result: it is the human-qrels ordering against
which the LLM assessor's ordering is compared in §4.5. By the primary nDCG@5 the order is
hybrid (0.525) > pedagogical (0.504) > BM25 (0.489) > dense (0.476); by Recall@5 it is
hybrid (0.411) > pedagogical (0.377) > dense (0.373) > BM25 (0.370). In both, hybrid is first and
dense/BM25 are last, with the pedagogical retriever a close second — a consequence of its high pool
precision offsetting its lost ranking relevance.

### 4.4.2 Robustness of the retrieval verdicts to annotator behaviour

Because the H1 and H2 verdicts are read off labels from a severity-heterogeneous panel, each verdict
is re-derived under a menu of plausible annotator-behaviour scenarios. The question is not whether
the point estimates move — they do, slightly — but whether the direction of each verdict survives.

> Table 5. Retrieval verdicts under qrels-perturbation scenarios (H1 = hybrid − dense, nDCG@10;
> H2 = pedagogical − hybrid, nDCG@5). "Recalibrated" mean-centres each rater; "optimistic/pessimistic"
> resolve each multi-rated pair by max/min instead of the mean; leave-one-out drops each annotator in
> turn.
>
> | Scenario                         | α    | H1 (nDCG@10) | H2 (nDCG@5) |
> |----------------------------------|------|--------------|-------------|
> | Baseline (mean, t ≥ 2)           | 0.46 | +0.061       | −0.022      |
> | Threshold t ≥ 1                  | 0.46 | +0.061       | −0.022      |
> | Threshold t ≥ 3                  | 0.46 | +0.061       | −0.022      |
> | Recalibrated (severity removed)  | 0.46 | +0.061       | −0.022      |
> | Optimistic (max per pair)        | 0.46 | +0.064       | −0.022      |
> | Pessimistic (min per pair)       | 0.46 | +0.060       | −0.022      |
> | Leave-one-annotator-out (×10)    | 0.34–0.59 | +0.056 … +0.070 | −0.026 … −0.015 |

Across all sixteen scenarios the H1 advantage stays positive (nDCG@10 in [+0.056, +0.070]) and the
H2 deficit stays negative (nDCG@5 in [−0.026, −0.015]); neither verdict flips, and neither is
driven by any single annotator. The leave-one-out column doubles as a diagnostic of the agreement:
dropping the grade-1-defaulting or lenient raters raises α (to 0.55–0.59) while dropping the
panel-consistent raters lowers it (to 0.34–0.40), and α never exceeds 0.59 — confirming the
moderate ceiling is a property of a genuinely mixed-expertise panel, not one poor rater. With the
bootstrap intervals of §4.2–§4.3 excluding zero, both directions are unlikely to be sampling noise.
The one caveat the sensitivity analysis does not dissolve is the lexical-overlap question of §4.2,
which concerns the construction of the evaluation queries rather than their annotation.

## 4.5 H3 (reframed) — the LLM relevance-assessor

The reframed H3 asks whether a calibrated LLM relevance-assessor, scoring (query, chunk) pairs under
the same rubric the human panel used, can stand in for human labels well enough (i) to rank the
four retrievers as the human qrels do and (ii) to reach per-item agreement approaching the human
ceiling of §4.1. The success criterion is the ceiling, not a fixed 0.7 bar: the claim to defend
is that judge–human agreement lands inside the human range.

The assessor is built and run: it scores every (query, chunk) pair on the 0–3 rubric with Claude
Opus 4.8 under the locked prompt (reproduced in Annex B), grading all 1,565 pairs twice (3,130
judgments, zero errors) to produce the LLM qrels used below. Because the judge model exposes no
temperature parameter, reproducibility is established as test–retest across the two runs.

### 4.5.1 Primary validation — does the assessor reproduce the retriever ranking?

The headline H3 test is system-ranking agreement, the field's primary validation mode (Thomas et
al. 2024; UMBRELA): run the assessor to produce LLM qrels, recompute the metrics for all four
retrievers against them, and compare the ordering to the human-qrels ordering of §4.4.

> Table 6. Retriever ranking under human qrels vs. LLM-assessor qrels, by nDCG@5 (rank 1 = best;
> score in parentheses). The last rows give pairwise concordance over the six system pairs and
> Kendall's τ (coarse — only four systems).
>
> | Variant                     | Rank (human qrels) | Rank (LLM qrels) |
> |-----------------------------|--------------------|------------------|
> | Hybrid (RRF)                | 1 (0.525)          | 1 (0.571)        |
> | Pedagogical                 | 2 (0.504)          | 2 (0.557)        |
> | BM25                        | 3 (0.489)          | 4 (0.503)        |
> | Dense                       | 4 (0.476)          | 3 (0.524)        |
> | Pairwise concordance    | —                  | 5 / 6            |
> | Kendall's τ (coarse)    | —                  | +0.67            |

The decisive question is narrower than the table looks: does the LLM qrels reproduce the H1 verdict
(hybrid > dense) and the H2-retrieval verdict (pedagogical vs. hybrid)? On both counts it does.
H1 is reproduced: under the LLM qrels the hybrid still beats dense (+0.047 nDCG@5; +0.068
Recall@10 and +0.053 nDCG@10, the same direction and comparable magnitude as the human-qrels +0.061),
so the assessor would have returned the same H1 decision. The H2-retrieval verdict is reproduced:
the pedagogical retriever again ranks second on nDCG@5 and does not exceed hybrid (−0.014 nDCG@5 under
the LLM qrels, against −0.022 under the human qrels). Beyond the two registered verdicts, the full
four-system ordering agrees on 5 of 6 pairwise comparisons (Kendall's τ = +0.67); the single
discordance is the BM25↔dense pair at the bottom, which the LLM qrels rank dense (0.524) just
above BM25 (0.503) where the human qrels rank BM25 (0.489) just above dense (0.476). Two things make
this swap minor. First, it is between the two weakest systems, on a gap of hundredths, leaving the
top of the ranking — where the H1/H2 decisions live — untouched. Second, its direction is the
recognised assessor-circularity risk made visible: the LLM qrels are uniformly more generous to the
dense/semantic channel (dense nDCG@5 rises 0.476 → 0.524), the tilt recorded as a limitation of the
assessor in §4.5.2 — never an input to the H1/H2 conclusions, which use the human qrels only. The
headline is therefore that the calibrated assessor reproduces both decisions the human qrels are
used to make — the strongest and most relevant form of the H3 ranking claim.

### 4.5.2 Secondary validation — per-item agreement against the ceiling

The finer view places the assessor's per-item agreement against the human ceiling of §4.1:
Krippendorff's α (ordinal) for assessor-vs-panel labels, read against the panel-vs-panel α on the
same anchor items. This is reported as secondary precisely because a sub-ceiling α is expected,
not disqualifying — Faggioli et al. (2023) and Thomas et al. (2024) report LLM relevance judgments
agreeing with human assessors considerably yet frequently below human–human levels (Cohen's κ ≈
0.20–0.64 across prompts, against ≈ 0.52 human–human).

> Table 7. Assessor per-item agreement vs. the human ceiling: ordinal α and binary κ at the contested
> 1↔2 cut. "Like-for-like" scores the assessor against each raw human grade on the 155 anchor pairs by
> exactly the procedure that produces the human ceiling (no panel averaging).
>
> | Agreement                                              | α (ordinal) | binary κ (1↔2) |
> |--------------------------------------------------------|-------------|----------------|
> | Human ceiling — panel ↔ panel (155 anchor pairs)       | 0.46        | 0.26           |
> | Assessor ↔ individual human (155 anchor, like-for-like)| 0.59    | 0.40           |
> | Assessor ↔ panel (all 1,565 pairs, collapsed)          | 0.55        | 0.42           |
> | Assessor test–retest reliability (run 1 ↔ run 2)       | 0.97        | 0.96           |

On the secondary criterion the reading is stronger than its "expected to fall short" framing
anticipated: the assessor does not merely approach the human ceiling — it meets and exceeds it. On
the like-for-like comparison, assessor↔human α is 0.59 against the 0.46 panel↔panel ceiling, and
binary agreement at the 1↔2 cut is κ = 0.40 against 0.26; the collapsed all-pairs view corroborates
at 0.55. This is not an averaging artefact — the like-for-like number, which never averages the
humans, is the higher of the two. The mechanism is the one Voorhees (2000) anticipates: a single
calibrated, near-deterministic rater (test–retest α = 0.97) lands closer to each individual human, on
average, than two independently noisy humans land to each other. It is read against a
mixed-expertise ceiling: "exceeds the ceiling" means it exceeds the agreement this panel
achieves, the relevant bar for whether the assessor can stand in for these labels. It is also why the
success criterion was set as the ceiling and not the literal H3 α ≥ 0.70 bar of Chapter 1: that bar
is unreachable by the humans themselves on this mixed panel (0.46).

Two cautions are carried forward. First, the dense/semantic tilt is a recognised circularity
risk: the assessor's per-item agreement is high partly because it, like the dense retriever, rewards
semantic overlap, so a fraction of the agreement and the ranking reproduction may be shared bias
rather than shared correctness — which is why the assessor's qrels never enter the H1/H2 verdicts.
Second, the residual disagreement is overwhelmingly graded near-misses: 91% of assessor↔human anchor
comparisons are within one grade, and the off-by-≥2 cases (≈ 9%) are where the assessor's limitation
should be sought in future error analysis. The combined H3 verdict is therefore that the calibrated
assessor reproduces both human-qrels retrieval decisions and agrees with individual teachers above
the mixed-panel human ceiling, with a documented dense-channel tilt as its principal limitation — a
domain-transfer validation of the LLM-as-relevance-assessor method for this low-resource francophone
setting, not a claim that the judge is bias-free.

## 4.6 What is not a result here

To keep the contribution from being overread, the boundary of this chapter is stated explicitly.
Three strands are executed and reported above — H1, the H2 retrieval side, and the reframed H3 — and
all three are retrieval-and-evaluation results. None shows that the tutor generates better
answers. The following are specified in the methodology and carried as future work.

- The response-grading judge (original H3 / H3b). A four-criterion judge (factual accuracy,
  curriculum alignment, pedagogical quality, language register; 1–5) over complete generated
  responses. Its harness is built and unit-tested but unrunnable for want of (query, response)
  gold, which was never collected. It is a different instrument on a different annotation object
  from the §4.5 assessor and produces no result here.
- The H2 generation side. Whether the enforced theory–example mix translates into measurably
  better tutoring responses — the pedagogical-quality verdict §4.3 does not deliver — depends on the
  response judge or a student A/B and is deferred.
- H4 (frontier vs. SLM under grounding) and the student study (correctness, confidence shift,
  A/B preference) are likewise unexecuted; both depended on the (query, response) gold and the human
  cohort that were out of reach for the submission.
- Generation-quality numbers of any kind. The generator is built, and its V2 prompt was selected by
  a 27-call controlled comparison on three single-extract items (§M6); that comparison checks the
  prompt's behaviour, not the quality of tutoring answers.

Read together, the executed strands establish the retrieval-and-evaluation foundation on which
the generation-quality study is the immediate, fully-specified next step. The interpretation of that
boundary — why a thesis of infrastructure results is defensible under the constraint — is taken up in
Chapter 5.
