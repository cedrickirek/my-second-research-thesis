"""Dense (embedding-based) retriever over corpus chunks.

The "meaning" half of the hybrid. Where BM25 matches surface tokens, this
encodes each chunk into a vector with a French-capable sentence-transformer
and ranks chunks by cosine similarity to the query vector.

Model convention: query and passage texts may need a prefix (E5 family uses
"query: "/"passage: "; bge-m3 uses none), and embeddings are L2-normalized so
that cosine similarity is a plain dot product. Prefixes are inferred from the
model name (`prefixes_for_model`) unless passed explicitly, so switching models
is a `model_name` change, not a rewrite — and an E5 model is never silently run
without its prefixes. Per-model cache paths (`default_cache_path`) let several
models coexist without clobbering each other's embeddings.

Production model: intfloat/multilingual-e5-large (~2.2 GB, 1024-dim). Selected
over the multilingual-e5-small smoke placeholder on 2026-06-17: it tops the
open-weights French retrieval scores on MTEB-French at the E5 prefix convention,
so the swap was a one-line DEFAULT_MODEL change (the cache key includes the
model name, so it auto-invalidates and re-embeds). BAAI/bge-m3 scores higher but
uses prefix-free encoding; it is now selectable (`model_name="BAAI/bge-m3"`) and
slated for a head-to-head once the labelled set exists. See
decisions/2026-06-17-embedding-model-e5-large.md.

The encoder is injectable (the `model` argument) so unit tests can supply a
deterministic fake and run offline; production passes None and a real
SentenceTransformer is loaded lazily.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Protocol

import numpy as np

from src.corpus.metadata import Chunk
from src.retrieval.bm25_index import ScoredChunk

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "intfloat/multilingual-e5-large"

# Query/passage prefix conventions, by model family. The E5 family REQUIRES
# "query: " / "passage: " prefixes; BGE-M3 (and most non-E5 models) use none.
# Running an E5 model WITHOUT its prefixes — or a non-E5 model WITH them —
# silently degrades retrieval, so the prefixes are inferred from the model name
# unless the caller passes them explicitly.
E5_PREFIXES = ("query: ", "passage: ")
NO_PREFIXES = ("", "")
DEFAULT_CACHE_ROOT = "results/dense_cache"


def prefixes_for_model(model_name: str) -> tuple[str, str]:
    """Infer (query_prefix, passage_prefix) from the model name.

    E5 family -> "query: "/"passage: "; bge-m3 -> none. An unrecognized model
    defaults to no prefix but logs a warning, so a model with an unusual
    convention is never silently mis-encoded — pass prefixes explicitly to
    override.
    """
    name = model_name.lower()
    if "e5" in name:
        return E5_PREFIXES
    if "bge-m3" in name or "bge_m3" in name:
        return NO_PREFIXES
    logger.warning(
        "unknown embedding model %r: assuming no query/passage prefix. If this "
        "model needs prefixes, pass query_prefix/passage_prefix explicitly.",
        model_name,
    )
    return NO_PREFIXES


def model_slug(model_name: str) -> str:
    """Filesystem-safe form of a model id (``/`` and the like -> ``_``)."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model_name)


def default_cache_path(model_name: str, root: str | Path = DEFAULT_CACHE_ROOT) -> Path:
    """Per-model cache path, so different models never clobber each other."""
    return Path(root) / f"{model_slug(model_name)}.npz"


def _passage_key(model_name: str, chunk_ids: list[str], passages: list[str]) -> str:
    """Cache key tying a saved matrix to the model + exact corpus that built it.

    Any change to the model name, the set/order of chunk_ids, or any passage
    text changes the hash, so a stale cache can never be silently reused.
    """
    h = hashlib.sha256()
    h.update(model_name.encode("utf-8"))
    for cid, passage in zip(chunk_ids, passages):
        h.update(b"\x00")
        h.update(cid.encode("utf-8"))
        h.update(b"\x01")
        h.update(passage.encode("utf-8"))
    return h.hexdigest()


class SentenceEncoder(Protocol):
    """Minimal contract we rely on (satisfied by sentence_transformers)."""

    def encode(
        self,
        sentences: list[str],
        normalize_embeddings: bool = ...,
        convert_to_numpy: bool = ...,
    ) -> np.ndarray: ...


class DenseIndex:
    """Embedding index over a fixed list of chunks, ranked by cosine similarity."""

    def __init__(
        self,
        chunks: list[Chunk],
        model: SentenceEncoder | None = None,
        model_name: str = DEFAULT_MODEL,
        query_prefix: str | None = None,
        passage_prefix: str | None = None,
        embeddings_cache: Path | str | None = None,
    ) -> None:
        if not chunks:
            raise ValueError("cannot build a dense index over zero chunks")
        # Prefixes are inferred from the model name unless given explicitly, so a
        # model is never silently encoded with the wrong family's convention.
        inferred_query, inferred_passage = prefixes_for_model(model_name)
        query_prefix = inferred_query if query_prefix is None else query_prefix
        passage_prefix = inferred_passage if passage_prefix is None else passage_prefix
        self._chunk_ids = [c.metadata.chunk_id for c in chunks]
        self._query_prefix = query_prefix
        self._model = model
        self._model_name = model_name
        passages = [passage_prefix + c.text for c in chunks]
        key = _passage_key(model_name, self._chunk_ids, passages)

        cached = self._load_cache(embeddings_cache, key)
        if cached is not None:
            self._matrix = cached
        else:
            # Cache miss: encode now (the expensive step), then save for reuse.
            self._matrix = self._encode(passages)
            self._save_cache(embeddings_cache, key, self._matrix)

    def _ensure_model(self) -> SentenceEncoder:
        """Load the sentence-transformer lazily, only when actually needed.

        Imported lazily so tests with an injected model never pay the heavy
        sentence_transformers/torch import, and a cache hit that only needs the
        passage matrix can skip the model load until the first query.
        """
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _encode(self, texts: list[str]) -> np.ndarray:
        return self._ensure_model().encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )

    @staticmethod
    def _load_cache(path: Path | str | None, key: str) -> np.ndarray | None:
        """Return the cached matrix iff the file exists and its key matches."""
        if path is None or not Path(path).exists():
            return None
        try:
            with np.load(path, allow_pickle=False) as data:
                if str(data["key"]) != key:
                    return None  # model or corpus changed → stale, recompute
                matrix = data["matrix"]
            logger.info("loaded %d passage embeddings from cache %s", len(matrix), path)
            return matrix
        except Exception as exc:  # corrupt/old cache → recompute, don't crash
            logger.warning("ignoring unreadable embeddings cache %s: %s", path, exc)
            return None

    @staticmethod
    def _save_cache(path: Path | str | None, key: str, matrix: np.ndarray) -> None:
        if path is None:
            return
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, matrix=matrix, key=np.array(key))
        logger.info("cached %d passage embeddings -> %s", matrix.shape[0], path)

    def search(self, query: str, k: int = 5) -> list[ScoredChunk]:
        """Return the top-k chunks for a query, highest cosine similarity first.

        Ties are broken by chunk_id (ascending) for reproducibility.
        """
        q = self._encode([self._query_prefix + query])[0]
        sims = self._matrix @ q  # cosine similarity (vectors are L2-normalized)
        ranked = sorted(
            zip(self._chunk_ids, sims),
            key=lambda pair: (-pair[1], pair[0]),
        )
        return [ScoredChunk(cid, float(s)) for cid, s in ranked[:k]]
