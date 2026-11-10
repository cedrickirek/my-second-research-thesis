"""Build (query, retrieved-chunk) pairs for teacher relevance annotation (#12).

For each query, pool the top-k candidates from every retrieval variant
(BM25, dense, hybrid, instructional), take their union, and emit one annotation
record per (query, chunk). Teachers later assign a graded relevance label
(0-3) to each record; those labels are the gold relevance used by the H1/H2
retrieval metrics (#24-28).

Design (decided 2026-06-16):
- Relevance scale: graded 0-3 (0 non pertinent ... 3 repond directement).
  Supports nDCG@k and Recall@k (binarise at >=2). Definitions in README.md.
- Pool: union of top-`pool_depth` from BM25 + dense + hybrid + the instructional
  selection. Pooling across variants keeps the gold labels variant-neutral, so
  no single variant is advantaged by being the only source of judged chunks.
- Blind to variant: `retrieved_by` / `rank_hybrid` are stored for analysis but
  MUST be hidden from annotators (avoid provenance bias).
- Figures: chunks with `has_dropped_figure=True` are excluded by default
  (CLAUDE.md); override with --include-figures.

Gating (both now met): (a) the curated 100-query set lives at
data/eval/queries.jsonl; (b) the production French embedding model is
intfloat/multilingual-e5-large (DenseIndex default since 2026-06-17). The real
run pools against e5-large. --no-dense pools BM25 only, for environments without
the embedding model — useful to validate the format/logic, NOT a valid
annotation pool.

Run (from repo root):
  uv run python -m src.eval.relevance.build_pairs \
      --queries experiments/2026-06-16-query-set-build/queries_bac2025.jsonl \
      --out experiments/2026-06-16-retrieval-annotation-smoke/pairs.jsonl --limit 3
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from src.retrieval.bm25_index import BM25Index
from src.retrieval.corpus_loader import load_chunks
from src.retrieval.dense_index import DEFAULT_MODEL, default_cache_path
from src.retrieval.tokenizer_fr import FrenchTokenizer

logger = logging.getLogger(__name__)

DEFAULT_CORPUS = Path("data/corpus/chunks.jsonl")
DEFAULT_POOL_DEPTH = 10
CANDIDATES_PER_RETRIEVER = 20

# Graded relevance scale (annotators fill `relevance`); full rules in RUBRIC.md.
RELEVANCE_SCALE = {
    0: "non pertinent",
    1: "marginalement pertinent",
    2: "pertinent",
    3: "central",
}
# Rubric version stamped on every pair so labels are always traceable to the
# definition in force. Bump when RUBRIC.md changes (see RUBRIC.md § versionnement).
RUBRIC_VERSION = "v1.0"


def _meta(chunk):
    """Pull the annotation-facing metadata from a Chunk in one place."""
    m = chunk.metadata
    return {
        "chunk_id": m.chunk_id,
        "chunk_content_type": m.content_type.value,
        "chunk_topic": getattr(m, "topic", None),
        "chunk_source": getattr(m, "source", None),
        "chunk_heading": getattr(m, "heading", None),
        "has_dropped_figure": m.has_dropped_figure,
    }


def build_pairs_for_query(
    query: dict,
    *,
    by_id: dict,
    bm25: BM25Index,
    pool_depth: int,
    dense=None,
    hybrid=None,
    instructional=None,
    include_figures: bool = False,
) -> list[dict]:
    """Pool every variant's top-k for one query and emit annotation records."""
    qtext = query["text"]
    provenance: dict[str, set[str]] = {}
    hybrid_rank: dict[str, int] = {}

    def add(chunk_id: str, variant: str) -> None:
        provenance.setdefault(chunk_id, set()).add(variant)

    for hit in bm25.search(qtext, k=pool_depth):
        add(hit.chunk_id, "bm25")
    if dense is not None:
        for hit in dense.search(qtext, k=pool_depth):
            add(hit.chunk_id, "dense")
    if hybrid is not None:
        fused = hybrid.search(
            qtext, k=pool_depth, candidates_per_retriever=CANDIDATES_PER_RETRIEVER
        )
        for rank, f in enumerate(fused, 1):
            add(f.chunk_id, "hybrid")
            hybrid_rank[f.chunk_id] = rank
    if instructional is not None:
        for chunk in instructional.search(
            qtext, candidates_per_retriever=CANDIDATES_PER_RETRIEVER
        ).selected:
            add(chunk.metadata.chunk_id, "instructional")

    records: list[dict] = []
    for chunk_id in sorted(provenance):
        chunk = by_id.get(chunk_id)
        if chunk is None:  # pool can name an id not in the corpus map only on bugs
            logger.warning("pooled chunk_id %s absent from corpus", chunk_id)
            continue
        meta = _meta(chunk)
        if meta["has_dropped_figure"] and not include_figures:
            continue
        records.append(
            {
                "pair_id": f"{query['query_id']}__{chunk_id}",
                "query_id": query["query_id"],
                "query_text": qtext,
                "query_bucket": query.get("bucket"),
                "query_question_type": query.get("question_type"),
                "query_lecons": query.get("lecons"),
                "chunk_id": chunk_id,
                "chunk_text": chunk.text,
                "chunk_content_type": meta["chunk_content_type"],
                "chunk_topic": meta["chunk_topic"],
                "chunk_source": meta["chunk_source"],
                "chunk_heading": meta["chunk_heading"],
                # --- provenance: for analysis only, HIDE from annotators ---
                "retrieved_by": sorted(provenance[chunk_id]),
                "rank_hybrid": hybrid_rank.get(chunk_id),
                # --- annotator fills these ---
                "rubric_version": RUBRIC_VERSION,  # rubric in force for this label
                "relevance": None,  # 0-3, see RUBRIC.md
                "annotator_id": None,
                "annotated_at": None,
                "notes": None,
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queries", type=Path, required=True, help="query JSONL (#10 output)"
    )
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--out", type=Path, required=True, help="output pairs JSONL")
    parser.add_argument("--pool-depth", type=int, default=DEFAULT_POOL_DEPTH)
    parser.add_argument(
        "--limit", type=int, default=None, help="first N queries (smoke)"
    )
    parser.add_argument("--include-figures", action="store_true")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="dense embedding model id (e.g. BAAI/bge-m3); prefixes inferred from name",
    )
    parser.add_argument(
        "--no-dense",
        action="store_true",
        help="BM25-only pool (no embedding model). Format/logic smoke only — NOT a valid pool.",
    )
    parser.add_argument(
        "--embeddings-cache",
        type=Path,
        default=None,
        help="cache passage embeddings here (default: per-model path under "
        "results/dense_cache/); reused if model+corpus unchanged",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="ignore the embeddings cache"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    chunks = load_chunks(args.corpus)
    by_id = {c.metadata.chunk_id: c for c in chunks}
    logger.info("loaded %d chunks from %s", len(chunks), args.corpus)

    queries = [
        json.loads(line)
        for line in args.queries.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.limit is not None:
        queries = queries[: args.limit]
    logger.info("loaded %d queries from %s", len(queries), args.queries)

    bm25 = BM25Index(chunks, FrenchTokenizer())
    dense = hybrid = instructional = None
    if args.no_dense:
        logger.warning("--no-dense: pooling BM25 only. NOT a valid annotation pool.")
    else:
        # Built lazily so a missing model / no network degrades to a clear error
        # instead of failing before BM25 is even available.
        from src.retrieval.dense_index import DenseIndex
        from src.retrieval.hybrid import HybridRetriever
        from src.retrieval.instructional import InstructionalRetriever

        cache = (
            None
            if args.no_cache
            else (args.embeddings_cache or default_cache_path(args.model))
        )
        logger.info(
            "building dense index with %s (first run downloads the model)...", args.model
        )
        dense = DenseIndex(chunks, model_name=args.model, embeddings_cache=cache)
        hybrid = HybridRetriever(bm25, dense, rrf_k=60)
        instructional = InstructionalRetriever(hybrid, chunks)

    all_records: list[dict] = []
    pairs_per_query: list[int] = []
    for q in queries:
        recs = build_pairs_for_query(
            q,
            by_id=by_id,
            bm25=bm25,
            pool_depth=args.pool_depth,
            dense=dense,
            hybrid=hybrid,
            instructional=instructional,
            include_figures=args.include_figures,
        )
        all_records.extend(recs)
        pairs_per_query.append(len(recs))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for rec in all_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    variants = ["bm25"] + (["dense", "hybrid", "instructional"] if dense else [])
    avg = sum(pairs_per_query) / len(pairs_per_query) if pairs_per_query else 0
    logger.info("variants pooled: %s", ", ".join(variants))
    logger.info(
        "wrote %d pairs for %d queries (avg %.1f pairs/query, min %d, max %d) -> %s",
        len(all_records),
        len(queries),
        avg,
        min(pairs_per_query, default=0),
        max(pairs_per_query, default=0),
        args.out,
    )


if __name__ == "__main__":
    main()
