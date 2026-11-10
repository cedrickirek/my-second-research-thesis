# Chapter 6. Conclusion and Future Work

## 6.1 Summary of contributions

This thesis set out to test four hypotheses about a curriculum-grounded retrieval-augmented tutor
for Ivorian Terminale C mathematics. Under the constraints of a single-author MSc project and a fixed
deadline, three were executed on data in hand and one (H4) was deferred; the executed core is a
retrieval-and-evaluation foundation, reported honestly as such. The concrete contributions are:

1. A chunked, content-typed Terminale C mathematics corpus for a low-resource francophone
   curriculum — 722 chunks from the CIAM series with an OCR pipeline validated against a
   hand-transcribed sample, a content-type taxonomy, and a documented figure-dropping and leakage
   discipline (data card in Annex C).

2. A four-variant retrieval stack with two registered tests. BM25, dense (multilingual E5), their
   RRF hybrid, and a content-type-aware pedagogical retriever that enforces a
   theory-plus-worked-example mix. H1 was supported — hybrid beat dense by +0.049 nDCG@5 (95%
   bootstrap CI [+0.009, +0.093]), robust across every annotator-perturbation scenario, though the
   advantage is carried by the lexical channel and partly reflects overlap between the synthesised
   queries and the corpus. The H2 retrieval-side test was not met: the pedagogical retriever
   trailed hybrid slightly on relevance (−0.034 Recall@5, CI [−0.061, −0.007]) — a small,
   relevance-neutral cost of enforcing the theory–example mix, read as a necessary-condition check and
   not as the pedagogical-quality verdict, which per-chunk relevance cannot deliver.

3. A human relevance-annotation instrument and its agreement machinery — a 0–3 rubric based on
   a correct human solution, the disp10 overlap design over 1,565 (query, chunk) pairs labelled by a
   mixed panel of two teachers and eight Terminale C students, and tested Krippendorff's α / Cohen's κ
   implementations. The mixed-expertise inter-annotator ceiling is reported in §4.1.

4. A domain-transfer validation of the LLM-as-relevance-assessor method (the reframed H3): a
   protocol testing whether an LLM scoring (query, chunk) pairs on the same rubric can rank the four
   retrievers as the human qrels do (primary) and agree per-item near the human ceiling (secondary),
   with circularity contained by never letting the LLM qrels enter the H1/H2 verdicts. Verdict: the
   assessor (Claude Opus 4.8, 3,130 judgments over the 1,565 pairs) reproduced both human-qrels
   retrieval decisions — preserving H1 (hybrid > dense) and H2-retrieval (pedagogical ≤ hybrid),
   agreeing with the human ranking on five of six system pairs (Kendall's τ = +0.67) — and its
   per-item agreement with individual teachers (α = 0.59 on the anchor) landed above the
   mixed-expertise human ceiling (0.46), with a documented dense/semantic tilt as its principal
   limitation.

A methodological contribution runs through all four: the BUILT-vs-PLANNED discipline and the H3
reframe (§5.1) — rebuilding an unexecutable hypothesis onto data in hand rather than reporting an
under-powered or un-calibrated result — are themselves part of what the thesis demonstrates about
rigorous evaluation under constraint.

## 6.2 Answering the research questions

RQ1/H1 (retrieval channel) — supported on this corpus. RRF fusion of sparse and dense retrieval
beat dense-only by +0.049 nDCG@5, robust across every perturbation scenario; the qualification is that
the gain is carried by the lexical channel and partly reflects vocabulary overlap between the
synthesised queries and the corpus, so confirmation on real student queries is the natural next test.
RQ2/H2 (pedagogical retrieval) — retrieval-side necessary condition met in the weak sense; the
pedagogical-quality question is not answered here. The pedagogical retriever enforces its
theory-plus-example mix at a small, bounded relevance cost (−0.034 Recall@5), which establishes only
that the mix is achieved without large relevance loss — not that it tutors better, a verdict that
per-chunk relevance cannot deliver and that awaits the generation study. RQ3/H3 (evaluation
calibration) — supported. The calibrated LLM relevance assessor reproduced both human-qrels
retrieval decisions (Kendall's τ = +0.67) and agreed with individual teachers above the
mixed-expertise human ceiling, with a dense/semantic tilt recorded as its principal limitation.
RQ4/H4 (deployment feasibility) — deferred. The grounded frontier-versus-open generator comparison
is fully specified but not executed, for want of the (query, response) gold and compute out of reach
for this submission. The umbrella question — whether a curriculum-grounded RAG tutor for Ivorian
Terminale C mathematics can be built and rigorously evaluated under real constraints — is answered
affirmatively for its retrieval-and-evaluation foundation, with the generation-quality study its
immediate continuation.

## 6.3 Future work

The future work is not a wish-list; it is the set of fully-specified next steps the foundation was
built to enable, each blocked on a resource (human gold, a cohort, compute) rather than on an
unanswered design question. They are listed in the order in which they most directly extend the
executed core.

1. The response-grading judge (original H3 / H3b). The four-criterion judge — factual accuracy,
curriculum alignment, pedagogical quality, language register (1–5), over complete generated
responses — is already built and unit-tested but unrunnable for want of (query, response) gold,
which requires a fresh round of human response-annotation. This is the single most immediate next
step: it converts the relevance-assessor foundation into a response-quality evaluator. It is
additionally being attempted as a delegated freeroll; nothing in this thesis depends on its outcome,
but if it returns it upgrades to a reported H3b result.

2. The H2 generation side — the pedagogical-quality verdict. The central open question the
retrieval-side H2 leaves unresolved (§5.3): does the enforced theory–example mix produce better
tutoring answers, not merely a defensible retrieval set? This needs the response judge of (1) or the
student study of (4), and it is the result that would let the thesis claim a teaching benefit rather
than a retrieval property.

3. H4 — frontier vs. small open model under grounding. Whether grounding narrows the quality gap
between a frontier generator (Claude) and a small open-weight model (e.g. Llama-3-8B, Gemma-2-9B) via a
difference-in-differences over grounded vs. ungrounded responses, with latency and cost on a Pareto
frontier. It depends on the response judge of (1) as its scoring instrument.

4. The student evaluation. A cohort of 10–20 Terminale C students, with a session protocol
measuring correctness, pre/post confidence shift, and pairwise A/B preference between retrieval
variants, plus qualitative interview coding. This is the only strand that measures learning rather
than a proxy, and it requires consent (and parental consent for minors), a recruited cohort, and a
piloted protocol — none compressible into the submission window.

5. Corpus and modality extensions. Lifting the scope limits: ingesting geometry (excluded
here), handling figures rather than dropping them (a multimodal pipeline), broadening beyond the
single textbook to test generalisation, and tuning the pedagogical retriever's (k_theory,
k_example) split on a held-out slice with a reported Pareto frontier. A multi-turn tutoring setting
is the natural system-level extension.

6. Evaluation-methodology hardening. Quantifying, at full-corpus scale, the contamination and
worked-example tagging-gap estimates left pending (§5.6), beyond the n = 40 pilot bounds reported
here.

## 6.4 Closing

The thesis does not claim a better tutor; it builds and validates the foundation on which that claim
can be tested — a curriculum-grounded corpus, a measured retrieval stack, a human relevance
instrument, and a validated LLM evaluator — for a setting (francophone, low-resource, curriculum
mathematics) where such a foundation did not previously exist. The work it leaves undone is not a set
of loose ends but a specified research programme, and the discipline by which an unexecutable
hypothesis was reframed onto data in hand rather than abandoned or faked is, finally, the part most
worth carrying forward.
