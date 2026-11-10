"""Rough hallucinated-equation filter.

Goal: surface chunks whose LaTeX content is structurally suspicious, so
they can be deprioritised at retrieval time, audited manually, or
excluded from the held-out eval set. We intentionally do *not* drop the
chunks here — the v1 corpus is small and a noisy chunk is still useful
context for an LLM in most cases. The filter only annotates.

The flag set is deliberately rough and pattern-based. Each flag captures
a failure mode observed in the marker validation run on CIAM Terminale C
(see `experiments/2026-05-12-marker-validation-ciam-tc/writeup/methodology.md`,
§4.4 error taxonomy):

  * ``mismatched_delimiters``     — odd count of ``$`` in the chunk after
                                    accounting for block ``$$`` pairs.
  * ``unbalanced_braces``         — any extracted equation has ``{`` count
                                    != ``}`` count.
  * ``equations_without_prose``   — chunk has equations but almost no
                                    natural-language text around them.
                                    Cannot be retrieved by paraphrase.
  * ``suspicious_short_equation`` — equation is ≤2 chars (likely OCR
                                    garbage like ``$.$`` or ``$-$``).
  * ``layout_artefact_in_equation`` — known marker bleed patterns
                                    (``\\bullet``, ``-Si``, leading
                                    French connector inside the equation).
  * ``ocr_degeneration_loop``     — the chunk contains a sentinel left by
                                    ``src.ocr.clean`` where a vision-model
                                    repetition loop was excised (see the
                                    2026-06-09 trial). Unlike the others
                                    this is a *certain* signal of lost
                                    content, not a heuristic.

These are coarse signals, not proofs of hallucination. A chunk with
zero flags can still be wrong; a chunk with several flags can still be
useful. The data card reports the distribution of flag counts so
readers know how much of the corpus is suspect.
"""

from __future__ import annotations

import re

from src.ocr.clean import contains_loop_sentinel
from src.ocr.validation.metrics import EQ_REGEX, extract_equations, normalize_prose

# Patterns that should never appear inside a well-formed math expression
# but do appear in marker output where prose has bled into an equation.
# Drawn from the worst-case pairs in the marker validation run.
_LAYOUT_ARTEFACT_PATTERNS = [
    re.compile(r"\\bullet"),
    re.compile(r"-Si\\?\s"),  # "-Si\ A = A'"
    re.compile(r"\bSi\b"),  # bare French "Si" inside an eq
    re.compile(r"\bdonc\b", re.IGNORECASE),
    re.compile(r"\balors\b", re.IGNORECASE),
]

# A chunk with equations needs *some* surrounding prose to be retrievable
# by a French-language query. The threshold is intentionally low — we are
# only catching the degenerate case of a chunk that is almost entirely
# LaTeX with no anchoring text.
_MIN_PROSE_CHARS_WITH_EQ = 30
_SHORT_EQ_THRESHOLD = 2


def _count_unescaped_dollars(text: str) -> int:
    """Count ``$`` characters not preceded by a backslash."""
    return len(re.findall(r"(?<!\\)\$", text))


def mismatched_delimiters(text: str) -> bool:
    """True iff ``$`` markers do not pair up.

    Block ``$$ ... $$`` contributes 4 dollars (2 opening, 2 closing) and
    each inline ``$ ... $`` contributes 2, so a well-formed document has
    an even total count. An odd count means at least one delimiter is
    dangling, which usually corresponds to an OCR misread of an
    equation boundary.
    """
    return _count_unescaped_dollars(text) % 2 == 1


def unbalanced_braces(equations: list[str]) -> bool:
    return any(eq.count("{") != eq.count("}") for eq in equations)


def equations_without_prose(text: str, equations: list[str]) -> bool:
    """True iff the chunk has equations but trivial natural-language text."""
    if not equations:
        return False
    prose = normalize_prose(text)
    return len(prose) < _MIN_PROSE_CHARS_WITH_EQ


def suspicious_short_equation(equations: list[str]) -> bool:
    """True iff any equation is ``_SHORT_EQ_THRESHOLD`` characters or fewer.

    Short equations are not inherently broken — a reference to a variable
    ``$x$`` is fine — but in the marker output they are dominated by OCR
    noise (``$.$``, ``$-$``, ``$•$``). Flagging the whole class is the
    rough end of the rough filter, by design.
    """
    return any(len(eq.strip()) <= _SHORT_EQ_THRESHOLD for eq in equations)


def layout_artefact_in_equation(equations: list[str]) -> bool:
    return any(any(p.search(eq) for p in _LAYOUT_ARTEFACT_PATTERNS) for eq in equations)


def ocr_degeneration_loop(text: str) -> bool:
    """True iff a degeneration-loop sentinel is present in ``text``.

    The sentinel is inserted by :mod:`src.ocr.clean` wherever a vision-model
    repetition loop was excised. Unlike the other filters this is not a
    heuristic: its presence is proof that the chunk lost content to an OCR
    generation artifact.
    """
    return contains_loop_sentinel(text)


def hallucination_flags(text: str) -> tuple[str, ...]:
    """Run every filter and return the names of those that fired.

    Order is stable so the resulting tuple is suitable for diffing
    between runs.
    """
    equations = extract_equations(text)
    flags: list[str] = []
    if mismatched_delimiters(text):
        flags.append("mismatched_delimiters")
    if unbalanced_braces(equations):
        flags.append("unbalanced_braces")
    if equations_without_prose(text, equations):
        flags.append("equations_without_prose")
    if suspicious_short_equation(equations):
        flags.append("suspicious_short_equation")
    if layout_artefact_in_equation(equations):
        flags.append("layout_artefact_in_equation")
    if ocr_degeneration_loop(text):
        flags.append("ocr_degeneration_loop")
    return tuple(flags)


# Re-exported for callers that want to count equations without re-parsing.
__all__ = [
    "EQ_REGEX",
    "equations_without_prose",
    "hallucination_flags",
    "layout_artefact_in_equation",
    "mismatched_delimiters",
    "ocr_degeneration_loop",
    "suspicious_short_equation",
    "unbalanced_braces",
]
