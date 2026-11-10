# Scope: Terminale C only

Date: 2026-05-12

## Decision

The thesis targets **Terminale C** mathematics only. Not C+D. Not D.

## Rationale

1. **Most math-demanding track.** Terminale C is the Ivorian high-school
   track with the heaviest mathematics load (vs D, which is SVT/biology-
   weighted and takes less math). Building a RAG tutor against the C
   curriculum exercises the system on the hardest material in the BAC
   ecosystem — strongest test of retrieval, generation, and evaluation.

2. **Strongest Tutorly proof-of-concept.** Tutorly's marketplace value
   proposition lives or dies on its ability to support the students who
   demand the most from their tutors. C students are that audience. A tutor
   that holds up for C generalizes downward; the reverse is not true.

3. **Cleanest thesis narrative.** "We built and validated a tutor for the
   most math-intensive Ivorian Terminale track" is a sharper, more
   defensible claim than "we covered two tracks shallowly." It also makes
   the H2 instructional-retrieval contribution land harder, since C
   problems are exactly where worked-example pairing pays off.

4. **Corpus and BAC keys.** C BAC math papers have the cleanest official
   answer keys and the richest equation content — best fit for the OCR
   pipeline and for ground-truth construction.

## Correction of prior handoff

A handoff document dated 2026-05-12 narrowed scope from "Terminale C and D"
to **Terminale D only**. That was a mistake. The reasoning given there
(cleaner keys, equation-OCR contribution) all applies *more strongly* to C.
D was never the right choice. This decision supersedes that handoff.

## What this changes

- Corpus sourcing (Week 1): programme officiel + 5 years of BAC papers for
  **Terminale C**, not D.
- All retrieval, generation, judge, and student-evaluation work is anchored
  to C content. Students recruited for Week 5 evaluation should be
  Terminale C students.
- The proposal (`claude-generated-stuff/Research_Proposal_Cedric.docx`),
  the external-review briefing
  (`claude-generated-stuff/forgemini-fromClaude-Thesis_Briefing_for_Review.docx`),
  and the claude.ai Project instructions all need to be updated from
  "Terminale C and D" or "Terminale D" to **Terminale C**.
- `CLAUDE.md` updated in the same commit as this file.

## What this does not change

The four hypotheses (H1 hybrid retrieval, H2 instructional retrieval,
H3 calibrated judge, H4 grounding closes SLM gap), the 8-week timeline,
the 30 June 2026 submission deadline, and the LLM-as-judge + real-student
evaluation methodology are unchanged.