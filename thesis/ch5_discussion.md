# Chapter 5. Discussion and Limitations

## 5.1 What the thesis establishes, and the honest exposure

The contribution of this thesis is a retrieval-and-evaluation foundation for a
curriculum-grounded mathematics tutor in a francophone, low-resource setting: a chunked,
content-typed Terminale C corpus, four retrieval variants with a registered H1 test and a
pedagogical-retrieval H2 test on the retrieval side, a human relevance-annotation instrument with
its agreement machinery, and a domain-transfer validation of the LLM-as-relevance-assessor method.
These are real, executed contributions on data in hand.

The honest exposure — the one a juror is most likely to press, owned here rather than deflected — is
that none of the three executed results demonstrates that the tutor produces better tutoring
answers. H1 and the H2 retrieval side are about which passages are retrieved; the reframed H3 is
about whether an LLM can label relevance like a human. All three are necessary infrastructure for a
generation-quality study, and none is that study. This follows directly from the annotation object: a
relevance label on a (query, chunk) pair says nothing about whether a generated response is
pedagogically good, and the (query, response) gold that would license a response-quality claim was
never collected.

The defensible framing — a methodological strength, not a save — is that this is what can be
established rigorously under the constraint, and that it is the foundation the generation-quality
study (§5.7) is the immediate next step from. The alternative — an under-powered, un-calibrated
generation result on no gold data — would have been the less honest thesis. The H3 reframe is the
clearest instance of this discipline: an unexecutable hypothesis was rebuilt onto data in hand rather
than left to fail or faked.

## 5.2 Interpreting H1 (hybrid vs. dense)

The hybrid advantage holds (Table 2): +0.049 nDCG@5, with a 95% bootstrap CI of [+0.009, +0.093]
that excludes zero, robust across every label-perturbation scenario. The natural reading is that
lexical match contributes signal the dense channel misses — but the stratified analysis sharpens, and
partly undercuts, it. The gain is not concentrated on the hard-edge queries (Δ +0.015), where a rare
content-bearing token would be the deciding signal; it is largest on the simplest single-leçon
queries (+0.065). And the leakage-control rows do not corroborate external validity: the sparse
channel outperforms dense on the synthesised queries but underperforms it on the held-out real
exam questions, which share less vocabulary with their relevant chunks. The most honest interpretation
is therefore mixed: the hybrid advantage is real and statistically supported on this evaluation set,
but it is carried by lexical overlap that the synthetic-query construction inflates, so part of it may
not transfer to how a real student phrases a question. The dense channel, which holds up on the
held-out real queries, is the more conservative default. (The held-out slice itself, at n = 9 with a
CI of [−0.315, +0.097], is too small to settle the question either way.)

The claim is bounded to this corpus, these untuned hyperparameters, and the non-geometry,
text-only scope; confirming H1 on real student queries is the named next step.

## 5.3 Interpreting H2 (pedagogical retrieval, retrieval side)

The H2 retrieval-side result (Table 3) requires the most careful reading in the thesis, and the care
is built into the design rather than added after the fact.

nDCG@5 is not the pedagogical-quality verdict. The pedagogical retriever deliberately passes over
higher-relevance theory chunks to seat its two worked-example slots; it can therefore lose on nDCG@5
while assembling a better teaching context, or win with no teaching benefit. So the retrieval-side
result tests one thing only — whether the enforced theory–example mix is achieved without sacrificing
relevance — and the interpretation is modest in every branch: a small or null Δ means the mix is
imposed at little relevance cost (the favourable outcome), while a material loss is read against the
example-availability split, since a loss concentrated on example-poor queries (where the fallback
degenerates the retriever toward the baseline) would be a corpus-coverage artefact rather than a
refutation.

Observed: the favourable branch, essentially. The pedagogical retriever trails the hybrid by a
small margin — −0.022 nDCG@5, −0.034 Recall@5 (the latter's CI excludes zero) — and the fallback
fires on only 2 of 100 queries, so the marginal and conditional estimates coincide and the loss is not
a coverage artefact. The mix is imposed at a small, genuine, but bounded relevance cost; combined with
the finding that examples are judged as relevant as theory and that this retriever has the highest pool
precision of the four, the retrieval side reads as near-relevance-neutral, with the
pedagogical-quality question passing intact to the generation-side study (§5.7).

The conservative-bias caveat governs a null result. Because a pilot audit found some
`theory`-tagged chunks are in fact headingless worked examples, the hybrid baseline can surface
example-like content by chance, partially closing the gap the pedagogical retriever enforces. A null
retrieval-side H2 result would therefore be ambiguous — no true effect, or a baseline that absorbed
it — and the magnitude is not negligible: a manual audit (n = 40, seed 42) estimates ≈ 32% of the
`theory`-labelled chunks are headingless worked examples (95% CI 20–48%), about 12% of the 514-chunk theory bucket. Resolving the ambiguity is exactly
what the generation-side evaluation is for, which is why the pedagogical-quality claim is held pending
(§5.7).

## 5.4 Interpreting the reframed H3 (the relevance-assessor)

H3 asks whether an LLM can stand in for human relevance labels well enough to (i) rank the four
retrievers as humans do and (ii) agree per-item near the human ceiling. Two interpretive points hold
regardless of the figures.

The primary read is the ranking, not the coefficient. If the LLM qrels reproduce the H1 and
H2-retrieval verdicts (Table 6), the assessor is good enough for the exact decision it supports — a
stronger claim than any single agreement number; a high per-item α with the wrong ranking would be
less useful than a moderate α with the right one. On the executed run the LLM qrels reproduce both
registered verdicts, agreeing with the human ranking on five of six system pairs (Kendall's τ =
+0.67).

A sub-ceiling per-item α would have been expected — but the assessor exceeded the ceiling. The
literature reports LLM–human agreement frequently below human–human (Faggioli et al. 2023; Thomas et
al. 2024), which is why the success criterion was set as the ceiling, not a fixed 0.7 bar, read
against a mixed-expertise ceiling (two teachers, eight students). On the like-for-like anchor
comparison the assessor agreed with individual teachers above it (α = 0.59 vs. 0.46), so the
domain-transfer validation succeeds for this setting. The honest counterweight is the dense/semantic
tilt the assessor carries: part of that agreement may be shared semantic bias rather than shared
correctness, which is why the assessor's qrels never enter the H1/H2 conclusions.

Circularity is contained, not eliminated. LLM relevance labels may tilt toward the dense/semantic
channel, and reproducing a human ranking that already favours that channel is easier if the assessor
shares the bias. This is why the ranking agreement is read together with the per-channel breakdown, and
why the tilt is recorded as a limitation of the assessor. It never contaminates H1/H2, because
those verdicts are computed on the human qrels and never on the LLM qrels — the single most important
firewall in the evaluation design.

## 5.5 A worked failure case

One failure is documented concretely because it is visible directly in the labels and isolates a
specific, fixable mechanism. Query `bac2025-e6` (a hard-edge, held-out BAC-2025 item) is a
Diophantine problem — darts scoring 13 and 7 points, find the non-negative integer solutions of
$13x + 7y = 1000$. Exactly one chunk was judged relevant: `bac-2024-maths-serie-c-0009`, the
analogous worked solution from the 2024 paper, which is indexed (only 2025 is held out). So
the relevant content is in the corpus.

The instructive point is which retriever found it. The dense channel retrieves the 2024 chunk at
rank 1 (nDCG@5 = 0.83) — semantic similarity correctly matches the 2025 problem to its 2024
analogue despite different numbers. BM25 misses it (low lexical overlap between the two years'
phrasings). And the RRF hybrid demotes it out of the top-5 (nDCG@5 = 0.00): with only one channel
ranking the chunk highly, reciprocal-rank fusion averages dense's rank-1 against BM25's absent rank and
the chunk falls below the cut-off. The lesson is a fusion failure, not a coverage gap — a
single-query illustration of the §4.2 finding that the hybrid's advantage is carried by lexical
overlap, and that on held-out items where query-to-corpus vocabulary diverges the dense channel is
the more robust choice. It also shows the cost of RRF's channel-agnostic averaging — a chunk one
strong channel ranks first can be buried when the other is silent — a concrete motivation for the
score-aware or learned fusion flagged in future work.

## 5.6 Threats to validity

The threats consolidated in §M9 are restated here in order of how much they bound the conclusions.

Significance and robustness — now quantified. The paired query-level bootstrap is built: retrieval
differences carry 95% CIs, and the H1 nDCG@5/nDCG@10 and H2 Recall@5 intervals exclude zero while the
H1 Recall@5 and MRR intervals do not. Each verdict survives every label-perturbation scenario. With
significance and label-robustness addressed, the largest remaining caveat on H1 is no longer
statistical but one of external validity: the lexical-overlap finding means the hybrid advantage
may be partly a property of the synthesised queries, and a real-student-query evaluation is required to
settle whether it transfers.

Gold provenance and the mixed-expertise ceiling. The coverage qrels behind H1/H2 are single-rater
and mostly student-produced, and the ceiling is mixed-expertise. The mitigation is the rubric:
relevance is based on a correct human solution, model-independent, graded against fixed criteria
applied uniformly — so trustworthiness rests on that anchor rather than the rater's role. A
teacher↔student stratification is not pursued (the panel was not asked to adopt role-specific
stances); the residual risk is disclosed, not removed.

Assessor circularity and paraphrase sensitivity. Contained by the human-qrels firewall (§5.4),
with the dense-channel tilt and the single locked prompt's paraphrase sensitivity recorded as assessor
limitations.

Contamination and leakage. BAC 2025 is de-indexed to limit leakage; the baseline smoke test ran on
a small in-corpus subset and is calibration-only, not a result. Worked-example contamination is ≈ 32% of the
`theory`-labelled chunks (95% CI 20–48%, n = 40), about 12% of the theory bucket, which sizes the conservative bias on the
H2-retrieval contrast; a full-corpus estimate is future work.

Generation faithfulness — the V2 silent-passthrough. The V2 strict-faithfulness prompt flags only
errors the model has prior knowledge to detect; an error in content the model has not seen passes
through silently. The temperature-0 prompt comparison (§M6) observed this directly: all three
prompts reproduced a corrupted tile size without comment. On an OCR'd corpus where ~14.7% of chunks carry a hallucination flag, this is a
real limitation of the generation component — documented, not a bug — and it bounds any future
generation-quality claim, not the retrieval results here.

Corpus and scope limits. Figure-dropping (15.7% of chunks), the exclusion of geometry, and the
single-textbook source bind every claim to non-geometry, text-only Terminale C content from one
edition; a documented worked-example tagging gap bears specifically on H2. Roughly 100 queries and only
four retrievers limit statistical power and generality.

## 5.7 What the work does and does not license

The work licenses three claims: that a curriculum-grounded retrieval-and-evaluation pipeline for
Terminale C mathematics can be built and measured on real expert-adjacent labels; that the
hybrid-vs-dense and pedagogical-vs-hybrid retrieval questions can be answered on this corpus; and
that the LLM-as-relevance-assessor method can be validated for this domain by ranking agreement and
ceiling-relative per-item agreement.

It does not license any claim that the tutor generates better answers, that the theory–example mix
improves teaching, that a frontier generator's grounding advantage over a small open model holds here
(H4), or that students learn more. Each depends on the (query, response) gold or the human cohort that
were out of reach for this submission. They are not gaps discovered late; they are the fully-specified
next steps the foundation was built to enable, set out in Chapter 6.
