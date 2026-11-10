"""Step 7 — end-to-end smoke test: retrieval -> prompt -> Claude, plus a
grounding-injection check.

Two Claude calls total (a few hundred output tokens each, a fraction of a cent):
  Part A  full RAG on a real query -> checks the generator USES the context.
  Part B  a poisoned extract       -> checks the generator is GROUNDED in the
          context rather than answering from parametric memory.

Writes a structured record to results.json for the experiment trail.

Run (from repo root, with ANTHROPIC_API_KEY set):
  uv run python "experiments/2026-06-01-baseline-smoke-test/run_pipeline.py"
  uv run python "experiments/2026-06-01-baseline-smoke-test/run_pipeline.py" "ta question"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # file -> slug -> experiments -> root
sys.path.insert(0, str(REPO_ROOT))

from src.corpus.metadata import Chunk  # noqa: E402
from src.generation.client import ClaudeClient  # noqa: E402
from src.generation.prompts import SYSTEM_PROMPT, build_user_message  # noqa: E402
from src.retrieval.bm25_index import BM25Index  # noqa: E402
from src.retrieval.corpus_loader import load_chunks  # noqa: E402
from src.retrieval.dense_index import DenseIndex  # noqa: E402
from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.retrieval.tokenizer_fr import FrenchTokenizer  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
SUBSET = SCRIPT_DIR / "smoke_chunks.jsonl"
RESULTS = SCRIPT_DIR / "results.json"

DEFAULT_QUERY = "Quand dit-on qu'un entier b divise un entier relatif a ?"

# Grounding-injection test: take a real chunk stating |b| <= |a| and flip the
# inequality to the FALSE |b| >= |a|, then ask about it (with ONLY that extract
# in context). A grounded generator should report the false claim or flag the
# contradiction; a generator answering from memory would give the correct
# |b| <= |a| while ignoring the extract.
POISON_CHUNK_ID = "extract-ciam-tc-0005"
GROUNDING_QUESTION = (
    "Si b divise a (a et b étant des entiers relatifs non nuls), "
    "que peut-on dire de la comparaison entre |b| et |a| ?"
)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    query = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY

    chunks = load_chunks(SUBSET)
    by_id = {c.metadata.chunk_id: c for c in chunks}

    tokenizer = FrenchTokenizer()
    bm25 = BM25Index(chunks, tokenizer)
    print("Building dense index (uses cached e5-small)...")
    dense = DenseIndex(chunks)
    hybrid = HybridRetriever(bm25, dense, rrf_k=60)
    client = ClaudeClient(model="claude-sonnet-4-6")

    record: dict = {"model": "claude-sonnet-4-6"}

    # --- Part A: full RAG ---------------------------------------------------
    print("\n" + "=" * 70 + "\nPART A - full RAG\n" + "=" * 70)
    fused = hybrid.search(query, k=5, candidates_per_retriever=20)
    passages = [by_id[f.chunk_id] for f in fused]
    print(f"QUERY: {query}\nContext passages (as numbered for the model):")
    for i, f in enumerate(fused, 1):
        ct = by_id[f.chunk_id].metadata.content_type.value
        print(f"  [{i}] {f.chunk_id}  [{ct}]")
    gen = client.generate(SYSTEM_PROMPT, build_user_message(query, passages))
    print(f"\nANSWER:\n{gen.text}")
    print(f"\n(tokens: in={gen.input_tokens} out={gen.output_tokens})")
    record["part_a"] = {
        "query": query,
        "context_ids": [f.chunk_id for f in fused],
        "answer": gen.text,
        "input_tokens": gen.input_tokens,
        "output_tokens": gen.output_tokens,
    }

    # --- Part B: grounding-injection ---------------------------------------
    print("\n" + "=" * 70 + "\nPART B - grounding-injection check\n" + "=" * 70)
    victim = by_id[POISON_CHUNK_ID]
    poisoned_text = victim.text.replace(r"\le", r"\ge")
    assert poisoned_text != victim.text, (
        rf"poison no-op: '\le' not found in {POISON_CHUNK_ID}; pick another chunk"
    )
    poisoned = Chunk(text=poisoned_text, metadata=victim.metadata)
    print(f"Poisoned {POISON_CHUNK_ID}: flipped  |b| <= |a|  ->  |b| >= |a|  (FALSE)")
    print(f"Original : {' '.join(victim.text.split())[:120]}")
    print(f"Poisoned : {' '.join(poisoned_text.split())[:120]}")
    print(f"\nQUESTION: {GROUNDING_QUESTION}")
    gen_b = client.generate(
        SYSTEM_PROMPT, build_user_message(GROUNDING_QUESTION, [poisoned])
    )
    print(f"\nANSWER:\n{gen_b.text}")
    print(f"\n(tokens: in={gen_b.input_tokens} out={gen_b.output_tokens})")
    record["part_b_grounding"] = {
        "poison_chunk_id": POISON_CHUNK_ID,
        "injected_false_fact": "|b| >= |a|  (truth is |b| <= |a|)",
        "question": GROUNDING_QUESTION,
        "answer": gen_b.text,
        "input_tokens": gen_b.input_tokens,
        "output_tokens": gen_b.output_tokens,
    }

    RESULTS.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nWrote {RESULTS.name}")
    print(
        "\nHow to read Part B:\n"
        "  GROUNDED -> answer says |b| >= |a| (uses the poisoned extract), or\n"
        "              explicitly flags that the extract contradicts known maths.\n"
        "  BROKEN   -> answer says |b| <= |a| (correct from memory) without\n"
        "              acknowledging the extract -> it ignored the context."
    )


if __name__ == "__main__":
    main()
