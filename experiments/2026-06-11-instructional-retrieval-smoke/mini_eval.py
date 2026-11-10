"""Mini-eval (eyeball, not the H2 evaluation): hybrid vs instructional top-5.

Builds the real BM25 + dense + RRF hybrid over the full v2 corpus, wraps it
with the instructional composition layer, and prints both top-5s side by side
for a few hand-picked French queries. The question to eyeball: does forcing
2 example slots visibly pull worked examples into the result that plain
relevance ranking misses?

Run (from the repo root):
  .venv/Scripts/python.exe "experiments/2026-06-11-instructional-retrieval-smoke/mini_eval.py"
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.retrieval.bm25_index import BM25Index  # noqa: E402
from src.retrieval.corpus_loader import load_chunks  # noqa: E402
from src.retrieval.dense_index import DenseIndex  # noqa: E402
from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.retrieval.instructional import EXAMPLE_TYPES, InstructionalRetriever  # noqa: E402
from src.retrieval.tokenizer_fr import FrenchTokenizer  # noqa: E402

CORPUS = REPO_ROOT / "data" / "corpus" / "chunks.jsonl"
QUERIES = [
    "Comment calculer le module d'un nombre complexe ?",
    "Comment résoudre une équation différentielle du type y' = f(x) ?",
    "Qu'est-ce qu'une primitive d'une fonction ?",
    "Comment étudier les variations d'une fonction à l'aide de sa dérivée ?",
    "Loi binomiale : comment calculer la probabilité d'un nombre de succès ?",
]


def _line(rank: int, chunk) -> str:
    heading = " ".join(chunk.metadata.heading.split())[:52]
    return f"   #{rank} [{chunk.metadata.content_type.value:10}] {heading}"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    chunks = load_chunks(CORPUS)
    by_id = {c.metadata.chunk_id: c for c in chunks}
    print(f"Loaded {len(chunks)} chunks.")

    tokenizer = FrenchTokenizer()
    bm25 = BM25Index(chunks, tokenizer)
    print("Building dense index (first run downloads e5-small ~470 MB, then embeds 728 chunks)...")
    dense = DenseIndex(chunks)
    hybrid = HybridRetriever(bm25, dense, rrf_k=60)
    instructional = InstructionalRetriever(hybrid, chunks)
    print("Indexes ready.\n")

    for q in QUERIES:
        print("=" * 78)
        print(f"QUERY: {q}")

        hyb = hybrid.search(q, k=5, candidates_per_retriever=20)
        hyb_ex = sum(
            1 for f in hyb if by_id[f.chunk_id].metadata.content_type in EXAMPLE_TYPES
        )
        print(f"\n HYBRID top-5   (examples present: {hyb_ex})")
        for i, f in enumerate(hyb, 1):
            print(_line(i, by_id[f.chunk_id]))

        ins = instructional.search(q, candidates_per_retriever=20)
        print(
            f"\n INSTRUCTIONAL top-5   (theory={ins.n_theory} example={ins.n_example} "
            f"backfills={ins.backfills} fallback={ins.fallback_fired} "
            f"examples_in_pool={ins.n_example_in_pool})"
        )
        for i, c in enumerate(ins.selected, 1):
            print(_line(i, c))
        print()


if __name__ == "__main__":
    main()
