# Executive Summary

Context and problem. In Côte d'Ivoire the baccalauréat gates higher education, and its
science-intensive série C track is the most selective; yet support is unequal — qualified
teachers are scarce, and a competent private tutor costs about a month's minimum wage (≈ 110 €
[Gouv.CI, 2023]). Large language models offer an always-available, low-cost tutor, but a
general-purpose model applied naïvely to high-stakes curriculum mathematics drifts from the
prescribed Ivorian curriculum (methods or notation the student was not taught) and can
hallucinate fluent error precisely where a learner is least able to catch it. This thesis asks
what form of retrieval-augmented generation (RAG) can be adapted to such a curriculum and — the
harder question in a low-resource setting — how the resulting tutor can be evaluated rigorously
when domain-expert labels are scarce.

Approach. The work builds and evaluates a RAG tutor grounded in the CIAM Terminale C corpus
(the canonical regional textbook), scoped to non-geometry, text-only content: a
content-type-tagged corpus of 722 chunks with a validated OCR pipeline and data card; a
four-variant retrieval stack (BM25, dense multilingual-E5, their RRF hybrid, and a novel
pedagogical retriever enforcing a theory-plus-worked-example mix); and a human-calibrated,
model-independent relevance-evaluation framework. Of four hypotheses, three were executed on data
in hand; H4 (a grounded frontier-versus-small-model comparison) was only partly completed,
awaiting human-expert calibration. H3 was deliberately recast: rather than have an LLM grade
complete tutoring responses (needing a (query, response) gold set that could not be collected in
time), the LLM acts as a relevance assessor over (query, chunk) pairs — the same object a mixed
panel of teachers and Terminale C students already labelled.

Findings. H1 was supported — the hybrid beat dense-only retrieval by +0.049 nDCG@5 (95%
paired-bootstrap CI [+0.009, +0.093]), robust across every annotator-perturbation scenario,
though the gain is carried by the lexical channel and partly reflects vocabulary overlap between
the synthesised evaluation queries and the corpus (a documented threat to validity). The H2
retrieval-side test was not met: the pedagogical retriever trailed the hybrid slightly (−0.034
Recall@5, CI [−0.061, −0.007]) — a small, relevance-neutral cost of enforcing the mix, read as a
necessary-condition check rather than a refutation, since retrieval-side nDCG is neither
necessary nor sufficient for the pedagogical-quality claim. The reframed H3 was supported:
the calibrated LLM assessor (Claude Opus 4.8) reproduced both human-qrels retrieval verdicts
(four-system ranking concordant on five of six pairs, Kendall's τ = +0.67) and agreed with
individual teachers above the mixed-expertise human ceiling (α = 0.59 vs. 0.46), with a
documented dense-channel tilt as its principal limitation (§4.5).

Contribution and honest scope. The thesis contributes pedagogical retrieval (the
worked-example effect operationalised as a retrieval-time content-type selection policy); a
domain-transfer validation of the LLM-as-relevance-assessor method to this francophone,
low-resource setting; and a documented, reusable Ivorian Terminale C corpus and data card, the
first of its kind to the author's knowledge. It establishes the retrieval-and-evaluation
foundation on which the generation-quality study is the immediate, fully-specified next step.
