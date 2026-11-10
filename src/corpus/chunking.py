"""Section-aware chunker for OCR'd French math markdown.

The chunker walks the markdown top-down, treating every ``#`` heading as
a potential section boundary. Headings come in two flavours in the CIAM
corpus, and we have to tell them apart:

  * **Topic headings** are numbered: ``# 2 Divisibilité dans Z``,
    ``# 2.1. Multiples et diviseurs d'un entier relatif``. They carry
    the curriculum structure and feed the ``topic`` / ``section_path``
    metadata field. They do not, by themselves, start a new chunk.
  * **Content headings** are content-type keywords:
    ``# Définition``, ``# Propriété 1``, ``# Démonstration``,
    ``# Exemples``, ``# Remarque``. Each starts a new chunk and
    determines its ``content_type``.

This split — topic = "where in the curriculum am I" vs content = "what
kind of paragraph is this" — is what makes the H2 instructional
retrieval experiment possible. Without a clean ``content_type``, the
retriever has no way to ask for "the worked example that goes with the
property I just retrieved".

Anything that follows a content heading, up to the next heading of any
kind, belongs to that chunk. Material before the first content heading
(typically a top-level chapter title) is attached to the next chunk's
section_path but is not itself emitted, because it carries no content.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

from src.corpus.figures import has_figure_reference, strip_figure_references
from src.corpus.filters import hallucination_flags
from src.corpus.metadata import Chunk, ChunkMetadata, ContentType
from src.ocr.clean import contains_loop_sentinel
from src.ocr.validation.metrics import extract_equations

log = logging.getLogger(__name__)

# Captures ``#+`` then the heading text, on a single line. The level
# (number of leading ``#``) is the captured length of group 1.
_HEADING_REGEX = re.compile(r"^(#+)\s+(.*?)\s*$", re.MULTILINE)

# A topic heading starts with a section number like "2", "2.1",
# "2.1.3", optionally followed by a dot and the section title. The
# wildcard tolerates markdown emphasis around the number ("**2.2.**").
_TOPIC_NUMBER_REGEX = re.compile(
    r"^\**\s*(\d+(?:\.\d+)*)\s*\.?\s*\**\s*(.*)$",
)

# Keyword → ContentType. Match is done on the lower-cased, accent-
# stripped heading text and is anchored at the start of the string, so
# "Propriété 1" and "Propriétés 2" both map to THEOREM. Order matters
# only when keywords are prefixes of one another (none here).
_CONTENT_TYPE_KEYWORDS: list[tuple[str, ContentType]] = [
    ("definition", ContentType.DEFINITION),
    ("theoreme", ContentType.THEOREM),
    ("propriete", ContentType.THEOREM),
    ("proposition", ContentType.THEOREM),
    ("lemme", ContentType.THEOREM),
    ("corollaire", ContentType.THEOREM),
    ("demonstration", ContentType.PROOF),
    ("preuve", ContentType.PROOF),
    ("exemple", ContentType.EXAMPLE),
    # Worked-example cues beyond the bare "exemple" keyword. CIAM presents many
    # worked examples under an imperative ("Résoudre…", "Calculer…") or a
    # concrete "étude de la fonction …" heading that never starts with
    # "exemple", so the keyword classifier filed them as `theory` (H2
    # feasibility audit, 2026-06-10). These cues are imperatives or concrete
    # studies, which keeps precision high — "Étude algébrique" (a topic, no
    # "de") deliberately does not match.
    ("resolution", ContentType.EXAMPLE),
    ("resoudre", ContentType.EXAMPLE),
    ("etude de", ContentType.EXAMPLE),
    ("etude d'", ContentType.EXAMPLE),
    ("calculer", ContentType.EXAMPLE),
    ("determiner", ContentType.EXAMPLE),
    ("exercice", ContentType.EXERCISE),
    ("probleme", ContentType.EXERCISE),
    ("solution", ContentType.SOLUTION),
    ("corrige", ContentType.SOLUTION),
    ("remarque", ContentType.REMARK),
    ("note", ContentType.REMARK),
    ("notation", ContentType.REMARK),
]


_MARKDOWN_EMPHASIS_REGEX = re.compile(r"[*_`]+")

# A leading elided article ("L'Étude", "D'après") sits in front of the keyword
# and would block prefix matching; stripped (post-fold) before classification.
_LEADING_ARTICLE_REGEX = re.compile(r"^[ld]'\s*")


def _ascii_fold(text: str) -> str:
    """Lower-case, strip markdown emphasis, and strip diacritics.

    Used purely for the heading classifier so that ``Démonstration``,
    ``**Propriété**``, and ``_Remarque_`` all collapse to the same
    keyword form. The chunk text itself is preserved as-is.
    """
    folded = _MARKDOWN_EMPHASIS_REGEX.sub("", text)
    # Normalize curly apostrophes to a straight one *before* the ascii-encode
    # drops them, so a leading elided article ("L'Étude") stays detectable.
    folded = folded.replace("’", "'").replace("‘", "'")
    folded = unicodedata.normalize("NFKD", folded)
    folded = folded.encode("ascii", "ignore").decode("ascii")
    return folded.lower().strip()


def _classify_heading(heading: str) -> tuple[ContentType | None, str | None]:
    """Return (content_type, topic_title) for one heading.

    Exactly one of the two is non-None for any well-formed heading:
      * topic_title for numbered curriculum headings
      * content_type for keyword content headings

    Returns (None, None) for headings that match neither, which the
    caller can attach to the previous topic as descriptive prose.
    """
    folded = _ascii_fold(heading)
    if not folded:
        return None, None

    # Numbered heading? Treat as a topic regardless of any following text.
    m = _TOPIC_NUMBER_REGEX.match(heading)
    if m and m.group(1) and any(ch.isdigit() for ch in m.group(1)):
        title = m.group(2).strip() or m.group(1)
        return None, title

    # Strip a leading elided article ("L'Étude" -> "etude") so it does not
    # block prefix matching.
    candidate = _LEADING_ARTICLE_REGEX.sub("", folded)
    for keyword, ctype in _CONTENT_TYPE_KEYWORDS:
        if candidate.startswith(keyword):
            return ctype, None

    # OCR drop-cap tolerance: CIAM prints a large decorative initial letter that
    # marker sometimes loses, turning "Démonstration" -> "émonstration",
    # "Solution" -> "olution", "Exercices" -> "xercices". Match a keyword with
    # its first letter dropped, but only when the remaining stem is long enough
    # (>= 6 chars) that it cannot collide with an ordinary word.
    for keyword, ctype in _CONTENT_TYPE_KEYWORDS:
        stem = keyword[1:]
        if len(stem) >= 6 and candidate.startswith(stem):
            return ctype, None

    return None, None


@dataclass(frozen=True, slots=True)
class _Segment:
    """A raw heading + body span sliced out of the markdown."""

    heading: str
    body: str  # heading line excluded
    content_type: ContentType | None
    topic_title: str | None


def _segments(markdown: str) -> list[_Segment]:
    """Slice the markdown into (heading, body) segments.

    A segment runs from one heading line up to (but not including) the
    next heading line. Material before the first heading is discarded
    here — it is usually marker preamble — and re-introduced at the
    chunk level if needed.
    """
    matches = list(_HEADING_REGEX.finditer(markdown))
    out: list[_Segment] = []
    for idx, m in enumerate(matches):
        heading_text = m.group(2).strip()
        body_start = m.end()
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        body = markdown[body_start:body_end].strip()
        ctype, topic = _classify_heading(heading_text)
        out.append(
            _Segment(
                heading=heading_text, body=body, content_type=ctype, topic_title=topic
            )
        )
    return out


def _update_section_path(path: list[str], heading: str, new_title: str) -> list[str]:
    """Push/replace the topic stack based on a numbered heading.

    The depth of the section number ("2.1.3" → depth 3) determines
    where in the stack the new title sits. Deeper-than-current pushes;
    shallower-or-equal replaces, truncating any deeper entries.
    """
    m = _TOPIC_NUMBER_REGEX.match(heading)
    if not m:
        path.append(new_title)
        return path
    depth = m.group(1).count(".") + 1
    return path[: depth - 1] + [new_title]


def _build_chunk(
    *,
    chunk_id: str,
    subject: str,
    level: str,
    source: str,
    section_path: list[str],
    heading: str,
    body: str,
    content_type: ContentType,
) -> Chunk:
    """Assemble a Chunk + its metadata from one segment."""
    cleaned = strip_figure_references(body).strip()
    figure_flag = has_figure_reference(body)
    eqs = extract_equations(cleaned)
    flags = hallucination_flags(cleaned)
    # A loop excised by the cleaner can sit in the heading rather than the
    # body (e.g. "## Exercices ⟦OCR_LOOP_REMOVED⟧"); ``hallucination_flags``
    # only sees the body, so catch the heading case explicitly.
    if contains_loop_sentinel(heading) and "ocr_degeneration_loop" not in flags:
        flags = (*flags, "ocr_degeneration_loop")
    word_count = len(re.findall(r"\w+", cleaned, flags=re.UNICODE))
    topic = " > ".join(section_path) if section_path else "(unscoped)"

    metadata = ChunkMetadata(
        chunk_id=chunk_id,
        subject=subject,
        level=level,
        topic=topic,
        source=source,
        content_type=content_type,
        has_dropped_figure=figure_flag,
        section_path=tuple(section_path),
        heading=heading,
        char_count=len(cleaned),
        word_count=word_count,
        equation_count=len(eqs),
        hallucination_flags=flags,
    )
    text = f"# {heading}\n\n{cleaned}" if cleaned else f"# {heading}"
    return Chunk(text=text, metadata=metadata)


def chunk_markdown(
    markdown: str,
    *,
    subject: str,
    level: str,
    source: str,
    chunk_id_prefix: str = "chunk",
) -> list[Chunk]:
    """Produce a list of typed chunks from one markdown document.

    The returned chunks are ordered as they appear in the source. The
    section_path on each chunk reflects the most recent topic stack
    seen up to that point. Numbered headings never produce their own
    chunk; only content headings do.
    """
    section_path: list[str] = []
    chunks: list[Chunk] = []

    for idx, seg in enumerate(_segments(markdown)):
        if seg.topic_title is not None:
            section_path = _update_section_path(
                section_path, seg.heading, seg.topic_title
            )
            # Numbered topic headings do not themselves emit a chunk; their
            # bodies (if any non-empty) cascade to the next content heading.
            # In practice CIAM puts empty bodies under numbered topics.
            if seg.body:
                log.debug(
                    "Topic heading %r has non-empty body of %d chars; "
                    "attaching to next content chunk via section_path.",
                    seg.heading,
                    len(seg.body),
                )
            continue

        ctype = seg.content_type or ContentType.THEORY
        chunk_id = f"{chunk_id_prefix}-{idx:04d}"
        chunks.append(
            _build_chunk(
                chunk_id=chunk_id,
                subject=subject,
                level=level,
                source=source,
                section_path=list(section_path),
                heading=seg.heading,
                body=seg.body,
                content_type=ctype,
            )
        )

    return chunks
