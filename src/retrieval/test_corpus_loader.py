"""Unit tests for the JSONL corpus loader.

Run: uv run pytest src/retrieval/ -q
"""

import json

from src.corpus.metadata import Chunk, ChunkMetadata, ContentType
from src.retrieval.corpus_loader import chunk_from_dict, load_chunks


def _sample_chunk() -> Chunk:
    meta = ChunkMetadata(
        chunk_id="x-0001",
        subject="mathematics",
        level="Terminale C",
        topic="Divisibilité > Multiples",
        source="CIAM Ch.2",
        content_type=ContentType.DEFINITION,
        has_dropped_figure=False,
        section_path=("Divisibilité", "Multiples"),
        heading="Définition",
        char_count=42,
        word_count=8,
        equation_count=1,
        hallucination_flags=(),
    )
    return Chunk(text="Soit a = kb avec accents: éàù.", metadata=meta)


def test_round_trip_from_to_jsonl():
    # The loader must be the exact inverse of Chunk.to_jsonl.
    original = _sample_chunk()
    restored = chunk_from_dict(json.loads(original.to_jsonl()))
    assert restored == original  # frozen dataclasses compare by value


def test_load_chunks_reads_jsonl(tmp_path):
    p = tmp_path / "chunks.jsonl"
    p.write_text(_sample_chunk().to_jsonl() + "\n", encoding="utf-8")
    chunks = load_chunks(p)
    assert len(chunks) == 1
    assert chunks[0].metadata.chunk_id == "x-0001"
    assert chunks[0].metadata.content_type is ContentType.DEFINITION