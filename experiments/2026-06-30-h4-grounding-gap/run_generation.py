"""H4 generation run: does grounding close the frontier-vs-SLM gap?

Generates the 2x2 design over a fixed query sample:

    {grounded, ungrounded} x {SLM (Ollama mistral:7b), frontier (Claude Sonnet)}

- grounded   = hybrid retrieval (BM25 + e5-large dense, RRF) -> top-k chunks
               injected into the V2 faithfulness prompt.
- ungrounded = the SAME question with NO retrieved context (empty passages).
               This is the clean grounding ablation: only the presence of the
               retrieved extracts changes between the two conditions.

Reuses the canonical generation prompt (src.generation.prompts) and the hybrid
retriever (src.retrieval.*) so this run can never drift from the rest of the
pipeline. The dense index loads from the existing e5-large cache, so no
re-embedding happens. Generation is temperature=0 (both backends) with a fixed
seed for reproducibility.

H4 scope: this is an EXPLORATORY hypothesis. The judge that scores these outputs
(Gemini, separate script) is UNCALIBRATED for the response-grading task because
teacher response-grades were not collected in time — flagged as a limitation in
the writeup, not papered over here.

Cost: the frontier (Claude Sonnet) half is a paid API call per response. With
30 queries x 2 grounding conditions = 60 Claude calls (~1.5K in / ~0.5K out
each), roughly $0.30-0.50 total. The SLM half (Ollama) is local and free.
Per CLAUDE.md's hard rule, the cost was estimated and confirmed before running.

Run (from repo root, with ANTHROPIC_API_KEY set and `ollama serve` up):
  uv run python "experiments/2026-06-30-h4-grounding-gap/run_generation.py"
  uv run python "experiments/2026-06-30-h4-grounding-gap/run_generation.py" --n 5  # smoke
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # file -> slug -> experiments -> root
sys.path.insert(0, str(REPO_ROOT))

from src.generation.client import ClaudeClient  # noqa: E402
from src.generation.ollama_client import OllamaClient  # noqa: E402
from src.generation.prompts import SYSTEM_PROMPT, build_user_message  # noqa: E402
from src.retrieval.bm25_index import BM25Index  # noqa: E402
from src.retrieval.corpus_loader import load_chunks  # noqa: E402
from src.retrieval.dense_index import DenseIndex, default_cache_path  # noqa: E402
from src.retrieval.hybrid import HybridRetriever  # noqa: E402
from src.retrieval.tokenizer_fr import FrenchTokenizer  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
CORPUS = REPO_ROOT / "data" / "corpus" / "chunks.jsonl"
QUERIES = REPO_ROOT / "data" / "eval" / "queries.jsonl"
RESPONSES_OUT = SCRIPT_DIR / "responses.jsonl"
RUN_LOG = SCRIPT_DIR / "run.log"

SEED = 42
N_QUERIES = 30
TOP_K = 5
CANDIDATES = 20
FRONTIER_MODEL = "claude-sonnet-4-6"
SLM_MODEL = "mistral:7b"

logger = logging.getLogger("h4")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(RUN_LOG, encoding="utf-8"), logging.StreamHandler()],
    )


def load_queries(n: int) -> list[dict]:
    """Load all queries, drop figure-dependent ones, sample n with a fixed seed.

    requires_figure queries are excluded: the corpus is text-only (figures are
    dropped at chunk time), so a figure-dependent question can't be fairly
    grounded and would confound the grounding ablation.
    """
    with QUERIES.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    eligible = [r for r in rows if not r.get("requires_figure", False)]
    rng = random.Random(SEED)
    sample = rng.sample(eligible, min(n, len(eligible)))
    sample.sort(key=lambda r: r["query_id"])  # stable output order
    logger.info("sampled %d of %d eligible queries (seed=%d)", len(sample), len(eligible), SEED)
    return sample


def build_retriever() -> tuple[HybridRetriever, dict]:
    """Build the hybrid retriever over the full corpus, reusing the dense cache."""
    chunks = load_chunks(CORPUS)
    by_id = {c.metadata.chunk_id: c for c in chunks}
    tokenizer = FrenchTokenizer()
    bm25 = BM25Index(chunks, tokenizer)
    cache = REPO_ROOT / default_cache_path("intfloat/multilingual-e5-large")
    logger.info("loading dense index from cache (e5-large, %d chunks): %s", len(chunks), cache)
    dense = DenseIndex(chunks, embeddings_cache=cache)
    hybrid = HybridRetriever(bm25, dense, rrf_k=60)
    return hybrid, by_id


def generate_with_retry(client, system: str, user: str, label: str, attempts: int = 5):
    """One generation call with exponential backoff on transient failures.

    Long batch runs over a flaky network drop the odd connection (e.g. a DNS
    getaddrinfo failure mid-run). The underlying clients make a single call with
    no internal retry, so without this one blip kills a 2-hour job. We retry a
    handful of times with growing backoff; a persistent failure still raises so
    a real outage isn't silently swallowed.
    """
    delay = 5.0
    for attempt in range(1, attempts + 1):
        try:
            return client.generate(system, user)
        except Exception as exc:  # noqa: BLE001 — transient net/HTTP, retry then re-raise
            if attempt == attempts:
                logger.error("%s: giving up after %d attempts: %s", label, attempts, exc)
                raise
            logger.warning(
                "%s: attempt %d/%d failed (%s); retrying in %.0fs",
                label, attempt, attempts, exc, delay,
            )
            time.sleep(delay)
            delay = min(delay * 2, 60.0)


def load_done_triples(path: Path) -> set[tuple[str, str, str]]:
    """Read already-written (query_id, model_role, grounding) triples for resume.

    A crashed/interrupted run leaves a partial responses.jsonl; re-running skips
    the triples already done so we never re-pay for the slow completed SLM calls.
    """
    if not path.exists():
        return set()
    done: set[tuple[str, str, str]] = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            done.add((r["query_id"], r["model_role"], r["grounding"]))
    return done


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=N_QUERIES, help="number of queries")
    args = parser.parse_args()

    setup_logging()
    logger.info("=== H4 generation run: 2x2 grounding x model ===")

    queries = load_queries(args.n)
    hybrid, by_id = build_retriever()

    frontier = ClaudeClient(model=FRONTIER_MODEL)  # temp=0 by default
    slm = OllamaClient(model=SLM_MODEL)  # temp=0, seed=42 by default

    backends = {"frontier": frontier, "slm": slm}

    done = load_done_triples(RESPONSES_OUT)
    if done:
        logger.info("resume: %d responses already present, will skip those", len(done))

    n_written = 0
    n_skipped = 0
    with RESPONSES_OUT.open("a", encoding="utf-8") as out:
        for qi, q in enumerate(queries, 1):
            qid, text = q["query_id"], q["text"]

            # Retrieve once per query; reuse for both backends' grounded condition.
            fused = hybrid.search(text, k=TOP_K, candidates_per_retriever=CANDIDATES)
            passages = [by_id[f.chunk_id] for f in fused]
            grounded_user = build_user_message(text, passages)
            ungrounded_user = build_user_message(text, [])  # no context

            conditions = {"grounded": grounded_user, "ungrounded": ungrounded_user}

            for model_role, client in backends.items():
                for grounding, user_msg in conditions.items():
                    if (qid, model_role, grounding) in done:
                        n_skipped += 1
                        continue
                    label = f"{qid}|{model_role}/{grounding}"
                    t0 = time.time()
                    gen = generate_with_retry(client, SYSTEM_PROMPT, user_msg, label)
                    dt = time.time() - t0
                    rec = {
                        "query_id": qid,
                        "query_text": text,
                        "model_role": model_role,  # frontier | slm
                        "model": gen.model,
                        "grounding": grounding,  # grounded | ungrounded
                        "retrieved_chunk_ids": [f.chunk_id for f in fused],
                        "response": gen.text,
                        "input_tokens": gen.input_tokens,
                        "output_tokens": gen.output_tokens,
                        "latency_s": round(dt, 2),
                    }
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    out.flush()
                    n_written += 1
                    logger.info(
                        "[%d/%d] %s | %s/%s | %.1fs | %d out-tok",
                        qi, len(queries), qid, model_role, grounding, dt, gen.output_tokens,
                    )

    logger.info(
        "done: wrote %d new responses (%d skipped as already-done) -> %s",
        n_written, n_skipped, RESPONSES_OUT,
    )


if __name__ == "__main__":
    main()