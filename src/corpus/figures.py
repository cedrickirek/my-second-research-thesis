"""Detect dropped figures in OCR'd markdown.

Marker emits an image reference ``![](_page_<n>_<Picture|Figure>_<m>.jpeg)``
wherever the source PDF contained a figure, diagram, or photo, but it does
not OCR the figure's contents — the pixels are saved out as a sidecar
image and the markdown loses whatever information was in the figure.

For a curriculum tutor this is a meaningful loss: a "tracer la courbe de
f" exercise becomes unanswerable if the courbe is gone. We do not try to
recover the figure here; we only *flag* chunks that overlap such a
reference so that downstream retrieval can deprioritise them, the data
card can quantify the loss, and the eval can skip questions whose
ground-truth answer depends on the missing image.

The detector is markdown-only and pattern-based; it works on either the
raw marker output (where the references appear inline) or on
post-processed text that has kept the references intact.
"""

from __future__ import annotations

import re

# Marker writes "![alt](_page_10_Figure_35.jpeg)" or "..._Picture_...".
# The leading "!" plus square-bracketed alt distinguish images from
# ordinary markdown links; the underscore-prefixed filename pattern
# distinguishes marker sidecars from intentional inline images.
FIGURE_REF_REGEX = re.compile(
    r"!\[[^\]]*\]\(\s*(?:[^)]*[\\/])?"
    r"_page_\d+_(?:Picture|Figure)_\d+\.(?:jpe?g|png|gif|webp)"
    r"\s*\)",
    re.IGNORECASE,
)


def has_figure_reference(text: str) -> bool:
    """True iff ``text`` contains at least one marker-style figure reference."""
    return FIGURE_REF_REGEX.search(text) is not None


def count_figure_references(text: str) -> int:
    return len(FIGURE_REF_REGEX.findall(text))


def strip_figure_references(text: str) -> str:
    """Remove figure references so they do not pollute prose-quality metrics."""
    return FIGURE_REF_REGEX.sub("", text)
