# Chapter 2. Related Work

## 2.1 Retrieval-augmented generation and hybrid retrieval

Retrieval-augmented generation (RAG) couples a parametric language model with a non-parametric
retrieval step: at inference the model is conditioned on passages fetched from an external corpus,
so its output is grounded in retrieved evidence rather than parametric memory alone (Lewis et al.,
2020). Originally motivated by knowledge-intensive tasks, the same mechanism has become a standard
response to hallucination, because grounding gives the generator a verifiable source against which
its claims can be constrained and audited (Huang et al., 2025). This thesis adopts RAG for that
second reason — curriculum fidelity and faithfulness, not open-domain knowledge coverage.

The retrieval step admits a well-known design space. Sparse retrieval scores a query against
documents by lexical overlap, canonically BM25 (Robertson & Zaragoza, 2009). Dense retrieval
embeds query and document into a shared vector space and ranks by similarity, capturing semantic
relatedness that survives paraphrase and vocabulary mismatch (Karpukhin et al., 2020). The two have
complementary failure modes: sparse retrieval is precise on rare tokens — names, notation, theorem
labels — but brittle to wording; dense retrieval is robust to wording but can wash out the
exact-match signal mathematical content depends on. A hybrid retriever combines the two rankings,
commonly by Reciprocal Rank Fusion (RRF), which requires no score calibration between systems
(Cormack et al., 2009). That fusion outperforms either channel alone, on a French OCR'd mathematics
corpus dense with notation, is precisely what H1 tests.

Two conditions of the present setting are under-represented in this literature. First, almost all of
this work is benchmarked on English, whereas this corpus is French; the dense channel here relies on
a multilingual sentence-embedding model (multilingual E5; Wang et al., 2024), selected for French
retrieval quality. Second, retrieval for education — over curriculum material, evaluated for
pedagogical rather than topical relevance — is a comparatively thin literature. H1 therefore does not
propose a new retrieval mechanism; it asks whether an established one transfers to a francophone,
low-resource, notation-heavy curriculum corpus — an answer the English-language results do not
settle, because the very signal hybridisation recovers (exact lexical match on notation and theorem
names) behaves differently in OCR'd mathematics than in clean web text.

## 2.2 The worked-example effect and pedagogically structured retrieval

The second strand is an instructional-design literature, and it motivates the thesis's central
methodological contribution. Cognitive Load Theory holds that learning is constrained by the limited
capacity of working memory, and that formats which reduce extraneous load free capacity for the
schema construction that constitutes learning (Sweller, 1988). A repeatedly replicated finding is the
worked-example effect: for novices acquiring a problem-solving skill, studying worked examples — a
problem paired with a fully elaborated solution — produces better and more efficient learning than
solving the equivalent problems unaided (Atkinson et al., 2000). The pedagogical unit that supports a
novice is therefore not theory alone and not an example alone, but the pairing: the governing
principle (definition, theorem, or method) together with a demonstration of its application.

This is the premise behind H2. A Terminale C student working a problem must mobilise both the
underlying theory and a worked example of its use; a content-type-blind retriever can return five
theory passages and no example, or the reverse, degrading the tutor's instructional value
independently of each passage's topical relevance. The thesis's response — pedagogical
retrieval — is a retrieval-time selection policy that enforces a fixed mix of theory-type and
worked-example-type passages from the same fused pool as the hybrid baseline, differing only in what
kind of content fills the context window.

To the author's knowledge, the worked-example effect has not previously been operationalised as a
retrieval constraint. The instructional-design literature studies how to present worked
examples to a learner who already has them; the IR literature optimises topical relevance and is
indifferent to pedagogical content type. Pedagogical retrieval sits in that gap — importing a result
from cognitive science into the selection stage of a RAG pipeline. This is the sense in which C1 is
novel: not a new retrieval algorithm, but a content-type-aware selection policy whose objective is
pedagogical composition rather than relevance maximisation alone. The claim is one of specific
novelty, not of an empty field: educational RAG is active — surveyed by Li et al. (2025) — and recent
systems adapt retrieval to the learner. The closest neighbour, PRAG-EDU (Nguyen et al., 2026),
conditions retrieval and response complexity on a student's historical grades as a proficiency
signal — a different axis from the content-type composition proposed here. To our knowledge, no prior
method enforces a fixed theory-plus-worked-example content-type mix at the selection stage of a
curriculum-tutoring RAG pipeline.

The method is called pedagogical retrieval rather than instructional retrieval (the codebase
name) to avoid collision with the distinct instruction-following retrieval literature, where
"instruction" denotes a natural-language directive attached to a query, not a pedagogical worked
example.

## 2.3 LLM-based relevance assessment for retrieval evaluation

Evaluating retrieval requires relevance judgements: to compute Recall@k or nDCG@k one must know which
chunks are relevant to which query, and those labels are the answer key against which ranking is
scored. Producing them at scale is the classic bottleneck of IR evaluation, and a fast-moving
literature asks whether an LLM can produce them in place of human assessors.

Faggioli et al. (2023) frame a spectrum of human–machine collaboration in relevance judgement and
raise the circularity objection explicitly — that using an LLM to judge relevance may unfairly
reward systems that themselves rely on LLM-like semantic similarity. Thomas et al. (2024), from a
major commercial search team, supply the method this work most closely follows: take human relevance
feedback, search over LLM-and-prompt configurations for one whose judgements agree with it, then
label at scale; they report LLM assessors about as accurate as human labellers at predicting searcher
preferences, while cautioning that agreement is sensitive to prompt phrasing and that LLM labels can
be biased toward rankers incorporating embedding similarity. Upadhyay et al. (2024) provide
UMBRELA, an open reproduction built on an openly available frontier model, used for the TREC 2024 RAG
Track, with a companion large-scale study of LLM-assessment properties. Together these establish
LLM-as-relevance-assessor as an established and independently reproduced method.

This is the literature the reframed H3 is anchored to. H3 as executed does not propose LLM
relevance assessment — that method exists and has been reproduced. The contribution is a
domain-transfer validation: the method is carried into a setting the source literature does not
cover (francophone, low-resource, curriculum mathematics) and validated against a curriculum-
proficient human panel — two practising mathematics teachers with former and current Terminale C
students — rather than crowd or searcher labels, with the success criterion set by the human
agreement ceiling rather than a fixed threshold. Two lessons are imported directly: the assessor is
given the same formalised information need the panel used (the rubric), following the finding that
formalised topics improve human–LLM agreement, with the prompt and decoding locked and paraphrase
sensitivity recorded as a limitation; and the headline validation is system-ranking agreement —
whether LLM labels rank the four retrievers in the same order as the human labels — the field's
primary validation mode (Thomas et al.; UMBRELA), with per-item agreement against the human ceiling
reported as secondary.

The circularity concern is contained by design: because the retriever verdicts (H1, H2 retrieval
side) are computed on the human-panel qrels and never on LLM qrels, the assessor is the object
under test, never the source of truth for the retrieval conclusions. The dense/semantic-similarity
tilt Thomas et al. warn of is therefore recorded as a limitation of the assessor, not a contaminant
of H1/H2.

## 2.4 LLM-as-judge for open-ended response evaluation

A second, larger LLM-evaluation literature concerns grading open-ended generated responses, and
keeping it distinct from §2.3 is the methodological hinge of this thesis's evaluation design. The
canonical reference is Zheng et al. (2023), which studies using a strong LLM to judge chatbot
answers (MT-Bench) and pairwise preference battles (Chatbot Arena), reporting that a capable LLM
judge agrees with human preferences about as often as humans agree with one another. It also
documents the failure modes that make naïve LLM judging risky — position bias, verbosity bias, and,
most consequentially for a generator comparison, self-enhancement bias, the tendency to favour
outputs from the judge's own model family.

The two literatures differ in their annotation object, and conflating them was the error the H3
reframe corrected. Relevance assessment (§2.3) labels a (query, chunk) pair on a relevance scale;
the judgement is front-loaded into an answer key and subsequent scoring is mechanical. Response
judging grades a (query, full response) pair on a multi-criterion rubric — factual accuracy,
curriculum alignment, pedagogical quality, language register — and is itself the open-ended
judgement. A relevance label on a chunk says nothing about whether a generated answer tutors well.
The thesis's executed evaluation result is the relevance assessor of §2.3; the four-criterion
response judge is specified but not executed, documented as future work (H3b) alongside the
generation-side test of H2 and the H4 comparison it would have scored. The deferral is structural:
the response judge depends on a (query, response) gold set the teacher dispatch never produced (only
the (query, chunk) relevance package was sent and returned).

Self-enhancement bias is why the future judging framework is designed to be model-independent —
anchoring quality to a correct human solution and keeping any judge model outside the set of
generators it scores, so the H4 comparison cannot be won merely by sharing the judge's family
preferences (C2). That this circularity is weaker for relevance assessment than for response judging
is one more reason the reframed H3 was chosen as the executable result.

## 2.5 Positioning: the gap and this thesis's place in it

The four strands meet at a setting none individually covers. RAG and hybrid retrieval (§2.1) are
mature but developed on English, data-rich, open-domain text; the worked-example effect (§2.2) is a
robust pedagogical result not turned into a retrieval constraint; LLM relevance assessment (§2.3) and
response judging (§2.4) are established methods validated against crowd or general-preference labels
in English. This thesis assembles these strands for a francophone, low-resource, curriculum-specific
secondary-school mathematics tutor, evaluated with a small curriculum-proficient panel (two teachers
and eight former or current Terminale C students) over OCR'd notation-dense content — a combination
the source literatures do not jointly address.

The contributions locate against that gap as follows. C1 — pedagogical retrieval (H2) is the one
genuinely new method: the worked-example effect operationalised as a content-type selection policy
at retrieval time. C2 — a human-calibrated, model-independent evaluation framework (H3) adapts the
relevance-assessment method of §2.3 to a curriculum-proficient panel and a ceiling-based criterion,
and specifies the response-judge extension of §2.4 with its circularity safeguards. C3 — the
documented Ivorian Terminale C corpus and data card is a reusable artifact for a curriculum these
literatures have not served. C4 — the grounded frontier-versus-SLM specification (H4) frames the
deployment question they leave open for low-resource settings.

Consistent with the honesty discipline maintained throughout, the executed core is H1, the retrieval
side of H2, and the reframed H3 — three results resting on the corpus and the relevance labels
already in hand. The response judge of §2.4, the generation side of H2, and H4 in full are specified
and anchored to the literatures surveyed here, and carried as future work rather than claimed as
results.
