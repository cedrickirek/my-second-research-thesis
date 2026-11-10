"""Instructional retriever: a composition layer over the hybrid fused pool (H2).

H2 asks whether *instructional* retrieval — deliberately returning a theory
chunk together with its worked example — beats a plain relevance ranking. This
retriever is that intervention, and *only* that: it does not re-rank or re-score
anything. It takes the exact same fused candidate pool the `HybridRetriever`
produces (H1's output) and changes only the **selection policy** over it, so any
measured difference is attributable to instructional structure, not to a
different retriever.

Policy (locked in `decisions/2026-06-10-h2-instructional-retrieval.md`):

* Return **5** chunks = **3 theory-type + 2 example-type**, fixed (not tuned —
  tuning the split would turn the hypothesis test into a hyperparameter search).
* **theory-type** = {theory, theorem, definition, proof, remark};
  **example-type** = {example, solution}. `exercise` (a raw problem statement)
  is neither, so it is never selected here.
* **Fallback:** if a slot's type is under-supplied in the pool, backfill from the
  next-ranked eligible chunk of the *other* type so the result always holds 5
  (graceful degradation toward the hybrid baseline on example-poor queries).
  Every backfill is counted; the fallback rate is a reported result.

The slots are filled by fused rank within each type, and the final 5 are
returned in fused-rank order.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.corpus.metadata import Chunk, ContentType
from src.retrieval.hybrid import HybridRetriever

THEORY_TYPES: frozenset[ContentType] = frozenset(
    {
        ContentType.THEORY,
        ContentType.THEOREM,
        ContentType.DEFINITION,
        ContentType.PROOF,
        ContentType.REMARK,
    }
)
EXAMPLE_TYPES: frozenset[ContentType] = frozenset(
    {ContentType.EXAMPLE, ContentType.SOLUTION}
)


@dataclass(frozen=True)
class InstructionalResult:
    """The selected 5 chunks plus the bookkeeping the H2 eval reports."""

    selected: list[Chunk]  # final chunks, in fused-rank order
    n_theory: int  # theory-type chunks in the result
    n_example: int  # example-type chunks in the result
    n_example_in_pool: int  # example-type chunks available in the fused pool
    backfills: int  # slots filled cross-composition (fallback firings)

    @property
    def fallback_fired(self) -> bool:
        """True iff the intended 3+2 split could not be met from the pool."""
        return self.backfills > 0

    @property
    def example_available(self) -> bool:
        """True iff the pool had at least one example-type chunk.

        The H2 effect should be reported conditioned on this (see the decision
        record's eval-stage notes): on example-poor queries the retriever
        degrades to the hybrid baseline, so averaging over them dilutes the
        effect.
        """
        return self.n_example_in_pool > 0


class InstructionalRetriever:
    """Select 3 theory + 2 example from the hybrid fused pool, with fallback."""

    def __init__(
        self,
        hybrid: HybridRetriever,
        chunks: list[Chunk],
        n_theory: int = 3,
        n_example: int = 2,
        theory_types: frozenset[ContentType] = THEORY_TYPES,
        example_types: frozenset[ContentType] = EXAMPLE_TYPES,
    ) -> None:
        self._hybrid = hybrid
        self._by_id: dict[str, Chunk] = {c.metadata.chunk_id: c for c in chunks}
        self._n_theory = n_theory
        self._n_example = n_example
        self._theory_types = theory_types
        self._example_types = example_types

    def search(self, query: str, candidates_per_retriever: int = 20) -> InstructionalResult:
        """Compose the instructional top-(n_theory+n_example) for a query."""
        target = self._n_theory + self._n_example
        # Pull the whole fused pool (up to both retrievers' candidates), not just
        # a top-k, so an example ranked below position 5 can still be found.
        pool_size = max(target, 2 * candidates_per_retriever)
        fused = self._hybrid.search(
            query, k=pool_size, candidates_per_retriever=candidates_per_retriever
        )
        fused_order = {f.chunk_id: i for i, f in enumerate(fused)}

        # Eligible chunks in fused order, split into the two slot types.
        # `exercise` and anything unmapped fall through and are never selected.
        theory: list[Chunk] = []
        example: list[Chunk] = []
        for f in fused:
            chunk = self._by_id.get(f.chunk_id)
            if chunk is None:
                continue
            ctype = chunk.metadata.content_type
            if ctype in self._example_types:
                example.append(chunk)
            elif ctype in self._theory_types:
                theory.append(chunk)

        chosen = theory[: self._n_theory] + example[: self._n_example]
        chosen_ids = {c.metadata.chunk_id for c in chosen}

        # Fallback: backfill remaining slots from the next-ranked eligible chunk
        # of either type (in fused order) until the result holds `target`.
        backfills = 0
        if len(chosen) < target:
            for chunk in sorted(
                theory + example, key=lambda c: fused_order[c.metadata.chunk_id]
            ):
                if len(chosen) >= target:
                    break
                if chunk.metadata.chunk_id not in chosen_ids:
                    chosen.append(chunk)
                    chosen_ids.add(chunk.metadata.chunk_id)
                    backfills += 1

        selected = sorted(chosen, key=lambda c: fused_order[c.metadata.chunk_id])
        n_theory = sum(
            1 for c in selected if c.metadata.content_type in self._theory_types
        )
        n_example = sum(
            1 for c in selected if c.metadata.content_type in self._example_types
        )
        return InstructionalResult(
            selected=selected,
            n_theory=n_theory,
            n_example=n_example,
            n_example_in_pool=len(example),
            backfills=backfills,
        )
