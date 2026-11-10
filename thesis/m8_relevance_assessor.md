## M8. The LLM relevance-assessor (H3)

### M8.1 The reframed hypothesis and why it is executable

The original H3 asked whether an LLM could grade complete generated responses on the four-criterion rubric in agreement with experts (§2.4). That requires a (query, response)
gold set, which could not be produced on time. Only the (query, chunk) relevance package was dispatched and completed. With the deadline close it was reframed: the annotation object was changed but not the ambition; the LLM now produces relevance labels on (query,
chunk) pairs, the same object the human panel already labelled. Hence, the gold pairs exist, the
agreement machinery already runs on this object, and no new human labour is required:

> **H3 (reframed)**. A calibrated LLM relevance-assessor, scoring (query, chunk) pairs under the
> same rubric the human panel used, (i) gives the same H1 and H2-retrieval verdicts as the human qrels when the four retrievers are scored against its labels (ii) reaches per-item agreement with held-out human annotators that approaches the human inter-annotator ceiling.

The method is anchored to the information retrieval evaluation literature on LLM-as-relevance-assessor (Faggioli
et al. 2023; Thomas et al. 2024; Upadhyay et al. 2024; §2.3): the thesis does not propose
it but contributes its domain-transfer validation to a francophone, low-resource,
curriculum-mathematics setting with a curriculum-proficient panel rather than crowd labels.

### M8.2 The assessor: inputs, prompt, and decoding

The assessor is Claude Opus 4.8 (`claude-opus-4-8`). It is given each pair and asked for the same 0–3 score on the same
rubric the panel applied (§M7.2). Following the finding that a formalised statement of the
information needed improves human–LLM agreement (Thomas et al. 2024), it receives the rubric
itself (the guiding question, the "would a correct solution use this?", and the decision rules) as its
instruction, so human and machine judge against the same model-independent definition.
Three controls are fixed and reported with the run:

- **Decoding fixed, determinism tested**. The model exposes no
  `temperature`, so reproducibility is established by test–retest reliability rather than assumed: each item run
  twice and aggregated by the round-half-up mean (the self-consistency idea of Wang et al. 2023). Two runs is a deliberately coarse check, but stricter than the single-run protocol common in the literature; the measured reliability is reported with the results.
- **The prompt is locked** before the assessor sees any pair, and paraphrase sensitivity is
  recorded as a limitation (Thomas et al. report LLM relevance judgements can shift under
  re-wording). 
  The locked system prompt
  (sha256 `prompt_id = ba9d533a88b87292`, recorded in every run's `run_meta.json`) is reproduced
  verbatim in Annex B.
- No human pre-labelling precedes the assessor, and it never anchors the humans: the human
  gold is fixed first, then the assessor labels (§M7.4.4). This ordering is the H3 protocol.

### M8.3 Success criterion: the human ceiling, not a fixed threshold

A flat "Krippendorff's α ≥ 0.7" bar was initially set, but later updated: the claim to defend is that assessor–human agreement lands
inside the human-human range. In other words, the assessor agrees with held-out annotators about as well as they
agree with one another following the metrics defined (Krippendorff's α, Cohen's κ). This is the honest yardstick
because the literature consistently reports human–LLM agreement below human–human (Faggioli et
al. 2023; Thomas et al. 2024). Because
the panel is mixed, this ceiling is a mixed-expertise one and the assessor "approaching" it must be read in that light.

### M8.4 The two-step validation of the assessor

**Primary Validation**. The headline test is the field's
primary validation mode (Thomas et al.; UMBRELA; §2.3) and the one aligned with what the assessor is for. It is a system-ranking agreement instead of a per-item agreement, which is stronger and more relevant than a generic agreement coefficient. 
(1) run the assessor over the (query, chunk) set to produce LLM qrels
(two runs aggregated, no humans); (2) recompute Recall@5 and nDCG@5 for all four retrievers
on the LLM qrels, reusing the existing metric code; (3) compare the retriever ordering
under the LLM qrels to that under the human qrels (exact ordering agreement, pairwise
concordance, and the Kendall's τ meausre of sytem ranking similarity). If the LLM qrels reproduce the H1 (hybrid > dense) and
H2-retrieval verdicts, the assessor is demonstrably good enough for the exact decision it
supports. 
*Caveat*: with
only four systems an ordering statistic is coarse, so τ is read with care. The two orderings
and their agreement are reported with the results.

**Secondary validation**. Here comes the per-item agreement against the ceiling. This finer view places judge–human per-item agreement against the human–human agreement
on the anchor overlap (§M7.4.2): Krippendorff's α for assessor-vs-panel against panel-vs-panel α
on the same items. It is secondary (a sub-ceiling α is expected, not disqualifying as mentioned in §M8.3) and
serves to locate where the assessor diverges, broken down by the contested boundaries (the
1↔2 threshold especially). 

### M8.5 Circularity: the concern and why the design contains it

The literature raises a specific circularity risk (Faggioli et al. 2023; Thomas et al. 2024):
LLM-produced relevance labels may be biased toward retrievers that themselves rank by LLM-like
semantic similarity. For this case here, a tilt toward the dense channel over lexical BM25 can be expected. Hence, the design
contains this by making the verdicts of the H1 and H2 hypotheses on the human-panel qrels, never on the LLM
qrels. The tilt remains a limitation of the assessor itself: if its labels replaced human ones to compare retrievers, those that rank by semantic similarity could be favoured.

### M8.6 Scope of the claim

The reframed H3 validates an evaluator: whether an LLM can stand in for human relevance
labels well enough to rank retrievers as humans do. It does not show the tutor generates
better answers — that is the work of the response judge (original H3, now H3b; harness built and
unit-tested at `future_work/response_judge_h3b/`, but unrunnable without (query, response) gold;
§M10), the H2 generation side, and the H4 comparison, all carried as future work.
Together with H1 and the H2 retrieval side, the reframed H3 establishes the
retrieval-and-evaluation foundation on which that generation-quality study is the immediate
next step.
