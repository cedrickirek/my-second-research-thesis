## M7. Relevance rubric and annotation protocol

This section specifies the instrument behind the retrieval ground truth: the rubric, the
calibration pilot that revised it, the overlap design, and the dispatch under which labels were
collected. Agreement statistics are defined in §M9; the full rubric and protocol minutiae are
in Annexes A and M.

### M7.1 The annotation object

The unit is a (student question, retrieved passage) pair: a rater grades how relevant one
retrieved passage/chunk is to answering the query. These labels constitute the qrels (query relevance judgements) i.e: the human answer key
against which Recall@k and nDCG@k are computed to score each retriever by checking the chunks it returned. Those scores are what test H1 and the retrieval side of H2. After the H3 reframe the labels are also the gold against which the LLM relevance-assessor (§M8) is validated — which is why the definition below is engineered to be
model-independent.

### M7.2 Design choices: The rubric

#### M7.2.1 relevance definition: utility for a correct solution

The rubric anchors relevance to utility for a correct answer, not topical similarity. Hence for an annotator to judge if a pair is relevant or not,  they ask themselves the **guiding question**: "To answer the question correctly, would a written solution use this
retrieved passage?" (FR: « …une solution rédigée utiliserait-elle ce passage ? »). Therefore, relevance is judged by a curriculum-proficient human, independent of any model, not by what an LLM would find useful.
A model-preference gold would be unjudgeable for human annotators and would contaminate the two
comparisons the thesis must keep clean: validating the assessor against independent human
judgement (§M8) and the future frontier-vs-SLM comparison. This is the C2 model-independence
principle (§1.4; `decisions/2026-06-18-rubric-v1.0.md`), relied on throughout §M8.

#### M7.2.2 The 0–3 scale

As "relevance" has been defined, each pair receives a graded relevance score:

| Score | Meaning (gloss) |
|---|---|
| 3 — Sufficient | The passage's information alone suffices to answer all parts of the question. |
| 2 — Useful | A part of the passage clearly helps with a part of the question — including a required method/format (e.g. an empty variation table for a function study), or a same-method worked example with different numbers. It is important to note that a part of a passage could be completely off-topic, while another one is relevant; this is the case because some chunks are relatively big and contain a lot of diverse information or show different intuitions in solving exercises|
| 1 — Marginal | Same chapter/theme, but no part clearly helps; or only loosely related. The floor for "right area, wrong content." |
| 0 — Not relevant | Different chapter/theme, and nothing in the passage helps (e.g. a probability passage for an exponential/logarithm question). |

A same-chapter passage scores at least 1 (0 is reserved for a different chapter contributing
nothing); utility overrides topic upward (a part helping a part scores 2 even from another
chapter); a required method/format/procedure counts (2, or 3 if it answers the whole
question); and each passage is judged alone. The seven decision rules in full and the
four-level worked example are in Annex A and Annex M.A.

#### M7.2.3 Scientific grounding: a domain adaptation of a standard scale

The scale uses the standard graded-relevance scale of the TREC Deep Learning tracks,
whose four NIST assessor levels are reproduced verbatim by the Bing/UMBRELA LLM
relevance-assessor [@thomas2024; @upadhyay2024umbrela], mapping almost one-to-one:

| This rubric | TREC DL / Bing / UMBRELA |
|---|---|
| 3 — sufficient (answers all parts) | 3 — perfectly relevant: "dedicated to the query and contains the exact answer" |
| 2 — a part helps a part | 2 — highly relevant: "has some answer… may be unclear, or hidden amongst extraneous information" |
| 1 — same chapter, does not help | 1 — related: "related to the query but does not answer it" |
| 0 — different chapter, no help | 0 — irrelevant: "the passage has nothing to do with the query" |

Grade 1 ("right topic, but does not help") may look unusual, but it is TREC's standard "related" level. 
The rubric departs from TREC in two deliberate ways: 
- "same topic" means "same syllabus chapter", which is what separates 0 from 1
- A passage is relevant if a correct solution would use it (§M7.2). The question is "would a correct solution use this passage?", not TREC's "does it contain the answer?".

The chapter-level rule only decides between 0 and 1. Since Recall@k counts only grades ≥ 2 (§M7.2.4), it leaves Recall@k unchanged; in nDCG@k it changes a passage's gain from 0 point to 1 point, small next to 3 points for a grade 2 and 7 points  for a grade 3.



#### M7.2.4 From graded labels to metric relevance

Both rules were fixed before any results, so the threshold could not be chosen after the fact. Recall@k treats a passage as relevant only if it is graded 2 or 3; the 1↔2 boundary is therefore the relevance threshold, which is why the pilot focused on it (§M7.3). nDCG@k uses the grade itself: each passage earns 2^grade − 1 points (0, 1, 3 or 7), passages lower in the list count less (divided by log₂(rank + 1)), and the total is divided by the best score possible for that query, giving a value between 0 and 1. Both are implemented in src/eval/relevance/retrieval_metrics.py.



### M7.3 Calibration pilot of the rubric

Before the full dispatch, a pilot tested the rubric: two tutors independently graded 80 pairs (5 stratified queries). Agreement was measured with weighted Cohen's κ (more info in §M9), a two-rater agreement score corrected for chance. On the full 0–3 scale, κ = 0.704, and 96.2% of pairs were within one grade of each other. But when grades are reduced to relevant (≥ 2) or not, κ fell to 0.587 — the weak point, since ≥ 2 is the Recall threshold. Of the 32 pairs the tutors graded differently, 13 were split between 1 and 2; disagreements concentrated on property-heavy queries (e.g. a BAC integral-parity item).

Based on that pilot's result, the response was to reframe the guiding question to "would a correct solution use this?", adding the "je m'en sers" check (Annex A), sharpening the 0↔1 and 2↔3 boundaries, and adding a four-level worked example.

The final version writes down the oral clarifications given at dispatch, without changing the definition. It is the version the LLM assessor is prompted with (§M8), so machine and panel judge the same applied definition. Full changelog: Annex M.B and decisions/2026-06-18-rubric-v1.0.md.

### M7.4 Design choices: The annotation plan 
#### M7.4.1 The overlap design

Two demands pull against a fixed budget: coverage (every one of the 100 queries needs its
pairs labelled at least once, or the qrels behind Recall@k / nDCG@k are incomplete) and
agreement (an inter-rater statistic such as Krippendorff's α is only defined on items more
than one annotator graded). The design splits the work into two tiers, one per demand.
Assignment is by query, not by pair: each query's ≈ 15.7 passages go to a single grader, who reads the question once and then grades its passages one after another, each on its own (rule 6, Annex A). Pooling retrieved candidates and judging per-(query,
chunk) relevance is the standard IR evaluation method, used to build qrels since the earliest
TREC campaigns [@voorhees2000] and carried into retrieval-for-RAG benchmarking
[@upadhyay2024largescale].

#### M7.4.2 The anchor and coverage tiers

- Anchor (agreement) tier: a stratified-random 10 queries (≈ 157 pairs), each graded
  independently by 2 annotators. It yields both the
  human inter-annotator ceiling and, after the reframe, the judge–annotator calibration
  of the LLM assessor (§M8).
- Coverage tier: the remaining 90 queries (≈ 1,408 pairs), each graded by one
  annotator.
The H1/H2 metrics use all 100 queries, not just the 90 coverage ones. Anchor pairs enter the qrels as the average of their two grades, rounded half up.

Two raters per anchor pair is the minimum at which an agreement statistic is defined
[@artstein2008], a redundancy the pilot validates by reaching a usable κ = 0.70 at that
level.

The anchor is stratified-random, not hand-picked — its 10 queries mirror the 60/20/20
composition of the full set (§M3): 6 single-leçon, 2 multi-notion, 2 hard-edge. At 10 queries it spans only 7 of the 10 chapters, an accepted trade-off of the load
reduction (§M7.4.3) and a limitation on the generality of the ceiling figure.

#### M7.4.3 Load balancing of the query pairs and the design revision

The binding constraint is per-annotator load. In fact, a heavier 20-query × 5-rater first cut placed
~283 pairs on each annotator. Because of the raters' fatigue, it was rebalanced to the 10-query × 2-rater anchor plus 90
coverage queries (~172 pairs each, a ~39% reduction), accepting lower anchor redundancy and the
narrower chapter span. This is justified by the pilot's κ = 0.70 at redundancy 2. How queries were split between raters (the load arithmetic, the ±7% greedy allocation, the sliding-window rater pairing, and the seed-42 generation) is in Annex M.C.

#### M7.4.4 Dispatch, versioning, the panel, and bias control

The full **dispatch** covered 1,565 unique (query, chunk) pairs (`results/relevance_pairs.jsonl`), each stamped with its
`rubric_version` in case the rubric is changed later; counting the anchor tier's double-grading, this is 1,721 total 0–3
judgements to be made. The **rubric is frozen after dispatch** (any later change requires a version bump and
re-annotation) and annotator identities are anonymised. 

Crucially, the **panel** is not ten teachers but mixed and curriculum-proficient: two mathematics tutors, six former Terminale C students, and two current Terminale C
students. They were selected because the relevance task needs recognising whether a correct Terminale C solution would use a passage, i.e. recent mastery of exactly this curriculum. The consequence is that the coverage qrels
are panel-produced, predominantly by students, recorded as a limitation in §M9. 


**Regarding bias control**, two ordering choices protect the agreement machinery and, through it, H3. First, no LLM
pre-labelling of the human pass: annotators never see a machine-suggested grade before judging,
which would anchor them and inflate apparent judge–annotator agreement; the assessor labels pairs
only after the clean human gold is fixed, and that ordering is the H3 protocol (§M8). Second,
the response-grading track is out of scope here: this design covers (query, chunk) relevance
only; the tutor-answer multi-criterion grading is a separate track that was not dispatched
(§M10). Both keep the agreement statistic a measure of human judgement uncontaminated by model
output.
