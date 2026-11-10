# Decision Record — H3 Reframe to LLM-as-Relevance-Assessor

- **Date:** 2026-06-26
- **Status:** Accepted
- **Affects:** H2 (scope clarification), H3 (reframe), `../claude-generated-stuff/master_task_list.md`, Introduction ch.1, M5, M1–M4, future-work section, bibliography
- **Author:** Cedric (decision), drafted in Claude Chat session; ported to repo by Claude Code 2026-06-26.

---

## 1. Context

With the 30 June submission close, the original H3 was found to be unexecutable in time, for a reason that is structural rather than a matter of effort. The session clarified the cause, chose a reframe that runs on data already in hand, and decided how to handle the original H3. It also surfaced two pre-existing documentation errors that must be corrected before the oral.

The root issue is an annotation-object distinction that had been blurred across the task list and drafts (see §4). Resolving it is what made the path forward obvious.

---

## 2. Decisions

1. **H3 is reframed.** The LLM no longer grades generated *responses*. It produces *relevance labels on (query, chunk) pairs* — the same annotation object teachers already produced for the retrieval qrels. H3 becomes: *a calibrated LLM relevance assessor reaches agreement with held-out teachers on (query, chunk) relevance that approaches the teacher–teacher agreement ceiling.*

2. **The success criterion is the ceiling, not a fixed threshold.** The claim to defend is "judge–teacher agreement lands inside the human (teacher–teacher) range," with Krippendorff's α as the metric. The flat "α ≥ 0.7" bar is dropped as a pass/fail line (it is retained only as a loose reference point). Rationale in §3 and §6.

3. **System-ranking correlation is H3's primary validation axis; per-item agreement is secondary.** The headline test is whether LLM-generated qrels rank the four retrievers (dense / BM25 / hybrid / pedagogical) the same way teacher qrels do. Per-item α-vs-ceiling is reported as the secondary, finer-grained view. This adds one analysis not previously in the task list (flagged as new scope; see §10).

4. **H3 is anchored to the IR-evaluation (LLM-as-relevance-assessor) literature**, not the LLM-as-response-judge literature. Verified anchors in §5.

5. **The original H3 is kept as documented future work.** The response-grading judge, its four-criterion rubric calibration, and the difference-in-differences it would have fed (H4) are written into the thesis as specified-but-not-executed. They are not deleted.

6. **The original H3 is additionally delegated to a friend as a freeroll.** Nothing in the submitted thesis depends on it. If it returns before the deadline, it upgrades a future-work item to a result (report as H3b alongside the relevance-assessor H3a). If it does not, nothing is lost. Ownership and writeup remain Cedric's; the friend acts as RA-equivalent labor on Cedric's design (consistent with the individual-work rule).

---

## 3. Rationale

- The reframe runs entirely on the (query, chunk) qrels that are already dispatched and returned. **No new teacher annotation is required.** This is the single fact that makes H3 executable before 30 June.
- The teacher–teacher ceiling machinery (triple-annotated overlap) was already built on the *relevance* annotation. "Judge approaches the ceiling" therefore lands in exactly the data object already in hand — not a separate object that would have to be built.
- The reframe converts H3 from specified-but-not-executed into a real **Findings** result (the 4-point rubric bucket), which is where the marginal grade is available this late.
- Cost: H3 shifts from *pedagogical-response* evaluation toward *IR-evaluation methodology* — marginally further from the "this is a tutoring system" spine. Accepted, because an executed result beats an unexecuted one, and the anchoring (§5) gives it a clean research lineage.

---

## 4. The annotation-object distinction (root clarification)

Two annotation tasks were being conflated. They are entirely distinct objects:

1. **Retrieval-relevance annotation** — unit is a **(query, chunk)** pair. Teacher rates chunk relevance to the query on the 0–3 rubric (v1.0). Produces the qrels behind Recall@k / nDCG@k. Feeds H1 and the H2 *retrieval side*.
2. **Response-grading annotation** — unit is a **(query, full generated response)** pair. Teacher grades a complete tutoring answer on the four-criterion rubric (factual accuracy, curriculum alignment, pedagogical quality, language register). Would be the gold standard for the original H3 and the instrument for the H2 *generation side* and H4.

A relevance label on a chunk says nothing about whether a generated *response* is pedagogically good. The two are not interchangeable.

**Status of fact, confirmed this session:** only (query, chunk) relevance pairs have ever been created and dispatched, and they have returned. **No (query, response) pairs have ever been generated or dispatched.** The original H3 therefore has *no gold data in existence* — its blocker is upstream human annotation turnaround (a full week per the proposal's own #1 risk), which a delegate cannot compress into the days remaining. This is why the reframe, not extra effort, is the resolution.

---

## 5. Literature anchoring (verified 2026-06-26)

All four checked against authoritative records (ACM DL, arXiv, Microsoft Research, dblp). Final citation style to be set per HEC formatting.

1. **Faggioli et al. (2023)**, "Perspectives on Large Language Models for Relevance Judgment," ICTIR '23, pp. 39–50, ACM. doi:10.1145/3578337.3605136; arXiv:2304.09161. Opens the question; defines a human–machine collaboration spectrum; includes a pilot on LLM–human correlation; explicitly raises the circularity objection.
2. **Thomas et al. (2024)**, "Large Language Models can Accurately Predict Searcher Preferences," SIGIR '24, pp. 1930–1940. doi:10.1145/3626772.3657707; arXiv:2309.10621. Microsoft/Bing. Supplies the *method*: take human feedback, select an LLM + prompt that agrees with it, then label at scale — the same shape as the reframed H3. Reports LLMs as accurate as human labellers; warns of unpredictable sensitivity to paraphrase and of bias toward rankers that themselves incorporate LLMs.
3. **Upadhyay et al. (2024)**, UMBRELA (open-source GPT-4o reproduction of Thomas et al.), arXiv:2406.06519. Authors: Upadhyay, Pradeep, Thakur, Craswell, Lin. Independent reproduction; used in the TREC 2024 RAG Track. *Verify whether a peer-reviewed version now exists before finalizing the bibliography — current record is a preprint.*
4. **TREC 2024 RAG Track** — UMBRELA used to produce the relevance judgments for the RAG test topics; companion study Upadhyay et al., "A Large-Scale Study of Relevance Assessments with Large Language Models," arXiv:2411.08275.

**Contribution framing (matches the locked "referee, not benchmark" principle):** LLM-as-relevance-assessor is an established, independently reproduced IR-evaluation method (Faggioli 2023 → Thomas 2024 → Upadhyay 2024). The thesis does not propose it. The contribution is a **domain-transfer validation** to a francophone, low-resource, curriculum-mathematics setting, using expert *teacher* labels rather than crowd/searcher labels, calibrated against the teacher–teacher ceiling.

**Action before defense:** read Thomas (2024) and Faggioli (2023) in full personally — a juror may ask Cedric to characterize the method he builds on, and that understanding cannot be outsourced.

---

## 6. Validation design for the reframed H3

- **Primary — system-ranking agreement.** Generate LLM relevance labels over the (query, chunk) set (automated, temperature 0, no teachers). Build LLM qrels. Recompute the existing retrieval metrics (nDCG@5 / Recall@5) for all four retrievers against the LLM qrels. Compare the resulting retriever ordering to the teacher-qrels ordering (Kendall's τ / ordering agreement). If LLM qrels reproduce the H1/H2 verdicts, the assessor is demonstrably good enough *for the exact decision it is used for*. This is the field's primary validation mode (Thomas, UMBRELA) and is more aligned with the thesis than generic per-item agreement.
- **Secondary — per-item agreement vs ceiling.** Judge–teacher α placed against the teacher–teacher α from the triple-annotated overlap. The literature reports human–LLM agreement frequently in the Cohen's κ ≈ 0.20–0.64 range, often well below human–human — so a sub-0.7 α here is *expected* and is not failure; it is exactly why the ceiling framing (Decision 2) replaces the fixed bar.
- **Best practice imported:** give the LLM assessor the same *formalized* statement of the information need that teachers used (the relevance rubric), per recent findings that formalized topics improve human–LLM agreement. Lock the assessor prompt and temperature; note paraphrase-sensitivity as a limitation.

---

## 7. Circularity — the concern and why the design contains it

- The concern is literature-grounded: Thomas (2024) warns that LLM-generated relevance labels may be biased toward retrieval models that themselves rely on LLM/embedding similarity. In this corpus the tilt would be toward dense/semantic similarity (the multilingual-e5 retriever).
- **Why it does not contaminate H1/H2:** the retriever verdicts (H1, H2 retrieval side) run on *teacher* qrels, not LLM qrels. The LLM assessor is the **object under test**, validated against teachers; it is never the source of truth for the retrieval conclusions. The bias is recorded as a limitation of the assessor only.
- This is weaker than generator–judge circularity (the failure mode the model-independent rubric in C2 was designed to avoid) and is disclosed, not hidden.

---

## 8. Consequences / what is now future work

- **Executed core of the thesis = H1, H2 (retrieval side), and the reframed H3.** Three real findings, all on the corpus + qrels already in hand.
- **Future work (specified, not executed):** original H3 (response-grading judge), H2 generation side (does the theory+example mix improve generated-response quality, via judge or student A/B), and all of H4. These already rested on the response judge, so the reframe *confirms* a gap rather than creating one.
- **Known exposure for the oral:** all three executed results are retrieval/evaluation-infrastructure results — none yet shows the tutor *generates* better answers. Prepared framing: this thesis establishes the retrieval and evaluation *foundation*; the generation-quality study is the immediate, fully-specified next step it was designed to enable.

---

## 9. Documentation errors surfaced (must fix before oral)

1. **Task #16 overstates the dispatch.** It reads "Dispatch full teacher annotation task (responses + retrieval relevance)." Only retrieval relevance was dispatched. Correct to retrieval relevance only; move the responses side to future work.
2. **Draft "dispatched and returned" language is ambiguous.** Introduction ch.1, M5 §M5.6, and M4 §M4.4 all say the teacher-annotation package was "dispatched and returned." This must read explicitly: *relevance-annotation package (query, chunk) dispatched and returned; response-grading annotation never dispatched (future work).*
3. **H2 primary-metric overstatement.** M5 §M5.6 calls nDCG@5 "the primary metric for H2." nDCG@5 is the primary *retrieval-side* metric only. It is neither necessary nor sufficient for the H2 pedagogical-quality claim, because the pedagogical retriever deliberately passes over higher-relevance theory chunks to seat the example slots — it can lose on nDCG@5 and still tutor better, or win and yield no tutoring gain. Soften the wording and keep the pedagogical-quality claim explicitly pending. Owned proactively at the oral.

---

## 10. Open follow-ups

- **New scope (flagged, approved):** add one H3 sub-item — system-ranking agreement between LLM qrels and teacher qrels across the four retrievers. To be added to `master_task_list.md` via an approved diff, not silently.
- **Pre-existing inconsistency to reconcile (not caused by this change):** teacher-annotator count is given as "10 teachers" in the M-drafts but "~5" in project notes. Confirm the true count for the relevance dispatch.
- **Proposal stays frozen.** `Research_Proposal_Cedric.docx` (2 May) is not retro-edited; it is the baseline against which this evolution is narrated. The divergence (H3 reframe, H2 retrieval-side scope) is documented here and explained in the thesis as methodological discipline under constraint.
- **H3 methodology section still to be written** (no M-section for H3 exists yet; this record is its spec): relevance-assessor protocol, ceiling + ranking-correlation validation, anchored to §5.

---

## Port note (Claude Code, 2026-06-26)

Ported verbatim from the Claude Chat decision. Repo-side consequences tracked separately:
- `master_task_list.md` edits proposed as an approved diff (per §10) — tasks 11/13/16/17/18/22/23 + new system-ranking sub-item.
- Verified teacher-annotator count for §10 (see `notes/2026-06-26-repo-audit.md` follow-up).
- Memory updated so future sessions read the reframed H3, not the original.