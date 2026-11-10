"""Step 5.5 — first real retrieval run for the baseline smoke test.

Loads the 10 frozen chunks, builds BM25 + dense + RRF hybrid, runs one French
query, and prints the top-5 with each chunk's component ranks. This is the
eyeball check: are the retrieved chunks obviously relevant?

Run (from the repo root):
  uv run python "experiments/2026-06-01-baseline-smoke-test/run_retrieval.py"
  uv run python "experiments/2026-06-01-baseline-smoke-test/run_retrieval.py" "ta propre question"
"""

from __future__ import annotations

import sys
from pathlib import Path

# Standalone script: its folder name isn't a valid module name, so it can't be
# run with `python -m`. Put the repo root on sys.path so `src` imports resolve.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.retrieval.bm25_index import BM25Index  # noqa: E402
from src.retrieval.corpus_loader import load_chunks  # noqa: E402
from src.retrieval.dense_index import DenseIndex  # noqa: E402
from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.retrieval.tokenizer_fr import FrenchTokenizer  # noqa: E402

SUBSET = Path(__file__).resolve().parent / "smoke_chunks.jsonl"
DEFAULT_QUERY = "Quand dit-on qu'un entier b divise un entier relatif a ?"


def main() -> None:
    # Force UTF-8 stdout so French accents and math symbols print cleanly on
    # Windows instead of crashing or showing mojibake.
    sys.stdout.reconfigure(encoding="utf-8")

    query = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY
    chunks = load_chunks(SUBSET)
    by_id = {c.metadata.chunk_id: c for c in chunks}
    print(f"Loaded {len(chunks)} chunks from {SUBSET.name}")

    tokenizer = FrenchTokenizer()
    bm25 = BM25Index(chunks, tokenizer)
    print("Building dense index (first run downloads e5-small, ~470 MB)...")
    dense = DenseIndex(chunks)
    hybrid = HybridRetriever(bm25, dense, rrf_k=60)

    print(f"\nQUERY: {query}\n" + "-" * 70)
    for rank, f in enumerate(hybrid.search(query, k=5, candidates_per_retriever=20), 1):
        c = by_id[f.chunk_id]
        fig = " [dropped-figure]" if c.metadata.has_dropped_figure else ""
        snippet = " ".join(c.text.split())[:140]
        print(
            f"#{rank}  {f.chunk_id}  rrf={f.rrf_score:.5f}  "
            f"bm25_rank={f.bm25_rank}  dense_rank={f.dense_rank}  "
            f"[{c.metadata.content_type.value}]{fig}"
        )
        print(f"     {snippet}...\n")


if __name__ == "__main__":
    main()