"""Unit tests for the French tutor prompt assembly (offline).

Run: uv run pytest src/generation/ -q
"""

from src.corpus.metadata import Chunk, ChunkMetadata, ContentType
from src.generation.prompts import SYSTEM_PROMPT, build_user_message


def _chunk(chunk_id: str, text: str) -> Chunk:
    meta = ChunkMetadata(
        chunk_id=chunk_id,
        subject="mathematics",
        level="Terminale C",
        topic="test",
        source="test",
        content_type=ContentType.DEFINITION,
        has_dropped_figure=False,
    )
    return Chunk(text=text, metadata=meta)


def test_user_message_numbers_passages_and_includes_question():
    msg = build_user_message(
        "Qu'est-ce qu'un multiple ?",
        [_chunk("c1", "Un multiple de b est..."), _chunk("c2", "Un diviseur de a est...")],
    )
    assert "[1] Un multiple de b est..." in msg
    assert "[2] Un diviseur de a est..." in msg
    assert "Question de l'élève : Qu'est-ce qu'un multiple ?" in msg


def test_system_prompt_enforces_grounding_in_french():
    assert "EXCLUSIVEMENT" in SYSTEM_PROMPT  # answer only from extracts
    assert "Ne corrige JAMAIS" in SYSTEM_PROMPT  # faithfulness: don't override the source
    assert "ne permettent pas de répondre" in SYSTEM_PROMPT  # insufficient-context fallback