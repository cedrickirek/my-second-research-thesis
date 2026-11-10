"""BM25 lexical retriever over corpus chunks.

Wraps rank-bm25's Okapi BM25 with the project's French tokenizer. The index
covers the chunk *text* only — a baseline choice. Enriching it with heading
or topic metadata is a deliberate future lever, not part of this baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from src.corpus.metadata import Chunk
from src.retrieval.tokenizer_fr import FrenchTokenizer


@dataclass(frozen=True)
class ScoredChunk:
    """A chunk id paired with the score a retriever assigned it.

    Shared return type: the dense retriever (Step 4) and RRF fusion (Step 5)
    produce and consume the same shape.
    """

    chunk_id: str
    score: float


class BM25Index:
    """Okapi BM25 index over a fixed list of chunks."""

    def __init__(self, chunks: list[Chunk], tokenizer: FrenchTokenizer) -> None:
        if not chunks:
            raise ValueError("cannot build a BM25 index over zero chunks")
        self._tokenizer = tokenizer
        # chunk_ids stay aligned by position with the tokenized corpus, so a
        # score at index i always maps back to chunk_ids[i].
        self._chunk_ids = [c.metadata.chunk_id for c in chunks]
        self._bm25 = BM25Okapi([tokenizer.tokenize(c.text) for c in chunks])

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        """Return the top-k chunks for a query, highest score first.

        Ties are broken by chunk_id (ascending) so results are reproducible
        even when several chunks score identically (e.g. an all-zero query).
        """
        scores = self._bm25.get_scores(self._tokenizer.tokenize(query))
        ranked = sorted(
            zip(self._chunk_ids, scores),
            key=lambda pair: (-pair[1], pair[0]),
        )
        return [ScoredChunk(cid, float(score)) for cid, score in ranked[:k]]