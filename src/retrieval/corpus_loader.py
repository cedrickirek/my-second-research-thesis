"""Load corpus chunks from JSONL into the typed Chunk objects of the schema.

The corpus build side (src.corpus) serializes Chunk -> JSONL via
Chunk.to_jsonl. This is the matching read side: JSONL -> Chunk. We reuse the
src.corpus.metadata types instead of defining a parallel chunk model, so
retrieval and corpus never drift apart on the schema.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.corpus.metadata import Chunk, ChunkMetadata, ContentType


def chunk_from_dict(payload: dict) -> Chunk:
    """Reconstruct one Chunk from a parsed JSONL record (inverse of to_jsonl)."""
    m = payload["metadata"]
    metadata = ChunkMetadata(
        chunk_id=m["chunk_id"],
        subject=m["subject"],
        level=m["level"],
        topic=m["topic"],
        source=m["source"],
        content_type=ContentType(m["content_type"]),
        has_dropped_figure=m["has_dropped_figure"],
        section_path=tuple(m.get("section_path", [])),
        heading=m.get("heading", ""),
        char_count=m.get("char_count", 0),
        word_count=m.get("word_count", 0),
        equation_count=m.get("equation_count", 0),
        hallucination_flags=tuple(m.get("hallucination_flags", [])),
    )
    return Chunk(text=payload["text"], metadata=metadata)


def load_chunks(path: Path | str) -> list[Chunk]:
    """Read a JSONL corpus file into a list of Chunk objects (utf-8)."""
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        return [chunk_from_dict(json.loads(line)) for line in f if line.strip()]