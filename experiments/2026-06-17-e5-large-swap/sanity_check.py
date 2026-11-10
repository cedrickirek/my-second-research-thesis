"""Sanity-check the e5-large embedding swap on the full 722-chunk corpus.

NOT an evaluation — no metrics, no ground truth. This confirms (a) the model
loads and embeds the production corpus, and (b) dense rankings for a handful of
representative French queries are topically sensible (the e5-small placeholder
gave weak rankings, e.g. "Qu'est-ce qu'une primitive ?" -> Propriété not
Définition; this is the regression check).

It builds the DenseIndex against the default cache path
(results/dense_cache/passages.npz) over the full corpus, so the expensive
~2.2 GB / 722-passage embedding is computed once here and reused by the real
#12 run (build_pairs.py) — same model, same chunk set => same cache key.

Run from repo root::

    uv run python "experiments/2026-06-17-e5-large-swap/sanity_check.py"
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.retrieval.corpus_loader import load_chunks  # noqa: E402
from src.retrieval.dense_index import (  # noqa: E402
    DEFAULT_MODEL,
    DenseIndex,
    default_cache_path,
)

HERE = Path(__file__).resolve().parent
CORPUS = REPO_ROOT / "data" / "corpus" / "chunks.jsonl"
# Per-model cache path — identical to what build_pairs.py uses, so this embed is
# reused by the real #12 run.
CACHE = REPO_ROOT / default_cache_path(DEFAULT_MODEL)

# Representative probes across leçons. Each is a natural French student question
# whose best match is topically obvious, so a human can eyeball correctness.
PROBES = [
    "Qu'est-ce qu'une primitive d'une fonction ?",
    "Comment calculer le module et un argument d'un nombre complexe ?",
    "Définition d'une suite arithmétique",
    "Comment résoudre une équation différentielle du second ordre à coefficients constants ?",
    "Quelles sont les propriétés du logarithme népérien ?",
]


def main() -> None:
    log_path = HERE / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_path, encoding="utf-8")],
    )
    log = logging.getLogger("e5_large_sanity")

    chunks = load_chunks(CORPUS)
    log.info("model=%s | corpus=%d chunks | cache=%s", DEFAULT_MODEL, len(chunks), CACHE)

    index = DenseIndex(chunks, embeddings_cache=CACHE)
    by_id = {c.metadata.chunk_id: c for c in chunks}

    for probe in PROBES:
        log.info("")
        log.info("QUERY: %s", probe)
        for rank, hit in enumerate(index.search(probe, k=5), 1):
            c = by_id[hit.chunk_id]
            snippet = " ".join(c.text.split())[:90]
            log.info(
                "  %d. %.4f  [%s/%s]  %s | %s",
                rank,
                hit.score,
                hit.chunk_id.rsplit("-", 1)[0],
                c.metadata.content_type.value,
                c.metadata.heading or "(no heading)",
                snippet,
            )

    log.info("")
    log.info("Done. Embeddings cached at %s (reused by build_pairs.py).", CACHE)


if __name__ == "__main__":
    main()
