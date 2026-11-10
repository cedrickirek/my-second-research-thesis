## 2026-05-13 — Figure handling in corpus

Decision: Figures (geometry diagrams, probability trees, function graphs)
are not ingested. Pure-text RAG only.

Rationale: Multimodal RAG is out of scope for an 8-week thesis. Cost of
alt-text annotation at corpus scale exceeds the benefit, given that most
theory content survives without figures.

Tradeoff accepted: A subset of BAC exercises ("soit la figure ci-contre")
become unanswerable. Mitigated by:
  - Tagging affected chunks with has_dropped_figure: true.
  - Excluding figure-dependent items from teacher annotation and student
    eval sets.
  - Documenting the limitation in the data card.

Reversibility: If Week 5 student eval shows figure-dependent questions are
a non-trivial fraction of the curriculum, reopen for either manual alt-text
or a multimodal generator branch. Default assumption: not reopened.

Operational rules (trigger words for the chunker, eval-set builder default):
see `CLAUDE.md § Corpus: figure handling`.