"""Schema for the metadata attached to every corpus chunk.

A chunk is the unit of retrieval. Its metadata governs three things:

  1. Filtering at index/query time (e.g. restrict to ``level == "Terminale C"``
     or ``content_type == "example"``).
  2. The H2 instructional retrieval experiment, which pairs a theory chunk
     with a worked example chunk at query time. That join is impossible
     without a clean ``content_type`` label, which is why this module
     commits to a fixed enum rather than free-form tags.
  3. Data-card auditing — the data card aggregates over these fields to
     report what is in the corpus and what is known to be lossy
     (``has_dropped_figure``, ``hallucination_flags``).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum


class ContentType(str, Enum):
    """Eight-way taxonomy for French math textbook content.

    Stays small enough to label by heading keyword + light prose heuristics,
    while preserving the theorem/proof and definition/example distinctions
    that H2 (instructional retrieval) depends on. See data card for the
    decision rationale.
    """

    THEORY = "theory"  # generic explanatory prose (fallback)
    DEFINITION = "definition"  # "Définition" sections
    THEOREM = "theorem"  # "Propriété", "Proposition", "Théorème", "Lemme", "Corollaire"
    PROOF = "proof"  # "Démonstration", "Preuve"
    EXAMPLE = "example"  # "Exemple(s)"
    EXERCISE = "exercise"  # "Exercice(s)", "Problème(s)"
    SOLUTION = "solution"  # "Solution", "Corrigé"
    REMARK = "remark"  # "Remarque(s)", "Note(s)", "Notation(s)"


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    """All non-text fields stored alongside a chunk in the corpus index.

    Required prompt fields: ``subject``, ``level``, ``topic``, ``source``,
    ``content_type``, ``has_dropped_figure``. The remaining fields are
    bookkeeping that the chunker can fill in for free and which the data
    card consumes.
    """

    chunk_id: str
    subject: str
    level: str
    topic: str
    source: str
    content_type: ContentType
    has_dropped_figure: bool
    section_path: tuple[str, ...] = field(default_factory=tuple)
    heading: str = ""
    char_count: int = 0
    word_count: int = 0
    equation_count: int = 0
    hallucination_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        """JSON-serializable representation (tuples → lists, enum → str)."""
        d = asdict(self)
        d["content_type"] = self.content_type.value
        d["section_path"] = list(self.section_path)
        d["hallucination_flags"] = list(self.hallucination_flags)
        return d


@dataclass(frozen=True, slots=True)
class Chunk:
    text: str
    metadata: ChunkMetadata

    def to_jsonl(self) -> str:
        """Serialize one chunk as a single JSON line (no trailing newline)."""
        payload = {"text": self.text, "metadata": self.metadata.to_dict()}
        return json.dumps(payload, ensure_ascii=False)
