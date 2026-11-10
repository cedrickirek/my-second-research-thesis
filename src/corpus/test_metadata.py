import json

from src.corpus.metadata import Chunk, ChunkMetadata, ContentType


def _meta(**overrides) -> ChunkMetadata:
    base = dict(
        chunk_id="c-0001",
        subject="mathematics",
        level="Terminale C",
        topic="Divisibilité dans Z > Multiples et diviseurs",
        source="CIAM Terminale C, Chapitre 2",
        content_type=ContentType.DEFINITION,
        has_dropped_figure=False,
    )
    base.update(overrides)
    return ChunkMetadata(**base)


def test_to_dict_renders_enum_as_string():
    d = _meta().to_dict()
    assert d["content_type"] == "definition"
    assert isinstance(d["content_type"], str)


def test_to_dict_tuples_become_lists():
    meta = _meta(
        section_path=("Arithmétique", "Divisibilité"),
        hallucination_flags=("mismatched_delimiters",),
    )
    d = meta.to_dict()
    assert d["section_path"] == ["Arithmétique", "Divisibilité"]
    assert d["hallucination_flags"] == ["mismatched_delimiters"]


def test_chunk_jsonl_is_single_line_json():
    chunk = Chunk(text="# Définition\n\nSoit a et b...", metadata=_meta())
    line = chunk.to_jsonl()
    assert "\n" not in line
    parsed = json.loads(line)
    assert parsed["text"].startswith("# Définition")
    assert parsed["metadata"]["content_type"] == "definition"
