"""Remove vision-model degeneration loops from marker OCR output.

When marker is run with its LLM/vision enhancement enabled, the model can
get stuck on an equation-dense page and emit the same short phrase over and
over until it hits a token ceiling. In the 2026-06-09 trial run this
produced lines like::

    # in a line of the latter of the latter of the latter of the latter ...

repeated ~145 times to a ~2 048-character ceiling, in English, inside a
French textbook. Three chapters (56, 256, 276) carry such loops; they are a
generation artifact, not content.

This module excises those loops. Design choices follow the corpus
philosophy of *flagging, not silently deleting* (see
``src/corpus/filters.py``):

  1. Detection keys on **consecutive** phrase repetition, not raw word
     frequency. This is what makes it safe over real math markdown: a table
     row ``| n | 0 | 1 | 2 |`` repeats ``|`` ten times but never
     *consecutively*, and a derivation that mentions ``x`` a dozen times
     spaces those mentions out. Neither trips the detector — only a phrase
     repeated back-to-back ``min_repeats`` times does.
  2. The repeated phrase must additionally be **wordy** (contain an
     alphabetic token of length >= 2), so a long run of identical numeric or
     symbol table cells can never be mistaken for a loop. Every loop
     observed in the trial was English words ("of the latter", "the same
     of", "the control of").
  3. Each excised run is replaced by a visible ``SENTINEL`` token rather
     than removed outright, so the downstream chunker can raise an
     ``ocr_degeneration_loop`` flag on the affected chunk and a human can
     see exactly where content was lost.

The default threshold (20 consecutive repeats) sits well below the observed
loops (135-169 repeats) and above anything legitimate seen in the corpus
(the largest benign consecutive run was 18), so removal is surgical.
Ambiguous near-threshold runs are deliberately *not* removed here; the
validation sweep reports them for manual review instead.

The cleaner never edits English-bleed words (e.g. "Addition *of*
multiplication" for "et"): that detection is lower precision and mutating
prose risks corrupting real content. Bleed is reported by the validation
sweep, not repaired here.
"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass

log = logging.getLogger(__name__)

# Distinctive, grep-able marker left where a loop was removed. Chosen to
# contain no ``$`` (so it cannot create or break a LaTeX delimiter), no
# markdown image syntax, and no whitespace (so it reads as a single token).
SENTINEL = "⟦OCR_LOOP_REMOVED⟧"

DEFAULT_MIN_REPEATS = 20
DEFAULT_MAX_PHRASE_WORDS = 4

# A phrase is "wordy" if it contains an alphabetic run of length >= 2,
# including accented Latin letters (French). Pure punctuation / digit runs
# (e.g. a column of zeros) are not wordy and are never treated as loops.
_WORDY_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}")


@dataclass(frozen=True, slots=True)
class LoopEvent:
    """One degeneration loop located and removed from the document."""

    line_number: int  # 1-based line in the *input* markdown
    phrase: str  # the repeated unit, space-joined
    repeats: int  # number of consecutive copies found
    removed_chars: int  # length of the excised run, in characters


@dataclass(frozen=True, slots=True)
class CleanResult:
    """Cleaned markdown plus a record of every loop that was excised."""

    text: str
    events: tuple[LoopEvent, ...]

    @property
    def loop_count(self) -> int:
        return len(self.events)

    @property
    def removed_chars(self) -> int:
        return sum(e.removed_chars for e in self.events)


def _is_wordy(phrase: str) -> bool:
    """True iff ``phrase`` contains an alphabetic token of length >= 2."""
    return _WORDY_RE.search(phrase) is not None


def _max_consecutive_run(
    words: list[str], start: int, max_phrase_words: int
) -> tuple[int, int]:
    """Best back-to-back repetition starting at ``words[start]``.

    Returns ``(repeats, phrase_len)`` for the phrase length ``k`` (in
    ``1..max_phrase_words``) whose immediate repetition starting at
    ``start`` covers the most words. ``repeats == 1`` means "no repetition".
    Ties are broken toward the shorter phrase so the reported unit is the
    minimal repeating cell.
    """
    n = len(words)
    best_repeats, best_k = 1, 1
    # A run needs at least two copies, so the phrase can be at most half the
    # remaining words long.
    max_k = min(max_phrase_words, (n - start) // 2)
    for k in range(1, max_k + 1):
        unit = words[start : start + k]
        repeats = 1
        j = start + k
        while j + k <= n and words[j : j + k] == unit:
            repeats += 1
            j += k
        covered = repeats * k
        if covered > best_repeats * best_k or (
            covered == best_repeats * best_k and k < best_k
        ):
            best_repeats, best_k = repeats, k
    return best_repeats, best_k


def _clean_line(
    line: str,
    *,
    min_repeats: int,
    max_phrase_words: int,
    sentinel: str,
) -> tuple[str, list[tuple[str, int, int]]]:
    """Excise loops from one line.

    Returns ``(cleaned_line, events)`` where each event is
    ``(phrase, repeats, removed_chars)``. A line with no loop is returned
    **verbatim** (byte-for-byte) with an empty event list, so legitimate
    content — including its original whitespace and markdown — is never
    reflowed.
    """
    words = line.split()
    # The shortest possible loop is ``min_repeats`` copies of a one-word
    # phrase, i.e. ``min_repeats`` words. Anything shorter cannot loop.
    if len(words) < min_repeats:
        return line, []

    out_tokens: list[str] = []
    events: list[tuple[str, int, int]] = []
    i, n = 0, len(words)
    while i < n:
        repeats, k = _max_consecutive_run(words, i, max_phrase_words)
        phrase = " ".join(words[i : i + k])
        if repeats >= min_repeats and _is_wordy(phrase):
            run_words = words[i : i + repeats * k]
            removed_chars = len(" ".join(run_words))
            events.append((phrase, repeats, removed_chars))
            out_tokens.append(sentinel)
            i += repeats * k
        elif repeats >= min_repeats:
            # Long but non-wordy run (e.g. repeated numeric cells): keep it
            # verbatim. Skip past it in one step to stay linear.
            out_tokens.extend(words[i : i + repeats * k])
            i += repeats * k
        else:
            out_tokens.append(words[i])
            i += 1

    if not events:
        return line, []
    return " ".join(out_tokens), events


def clean_degeneration_loops(
    markdown: str,
    *,
    min_repeats: int = DEFAULT_MIN_REPEATS,
    max_phrase_words: int = DEFAULT_MAX_PHRASE_WORDS,
    sentinel: str = SENTINEL,
) -> CleanResult:
    """Remove degeneration loops from an OCR'd markdown document.

    A *loop* is a wordy phrase of 1..``max_phrase_words`` words repeated
    back-to-back at least ``min_repeats`` times within a single line. Each
    loop is replaced by ``sentinel`` and recorded as a :class:`LoopEvent`.
    Everything else is preserved exactly.

    The operation is idempotent: running it on its own output is a no-op,
    because the sentinel breaks up any repeated phrase it sat inside.
    """
    cleaned_lines: list[str] = []
    events: list[LoopEvent] = []
    # split("\n")/join("\n") round-trips faithfully regardless of trailing
    # newline; we avoid splitlines() collapsing line-ending variants.
    for lineno, line in enumerate(markdown.split("\n"), start=1):
        new_line, line_events = _clean_line(
            line,
            min_repeats=min_repeats,
            max_phrase_words=max_phrase_words,
            sentinel=sentinel,
        )
        cleaned_lines.append(new_line)
        for phrase, repeats, removed in line_events:
            events.append(
                LoopEvent(
                    line_number=lineno,
                    phrase=phrase,
                    repeats=repeats,
                    removed_chars=removed,
                )
            )

    if events:
        log.info(
            "Removed %d degeneration loop(s), %d characters total.",
            len(events),
            sum(e.removed_chars for e in events),
        )
    return CleanResult(text="\n".join(cleaned_lines), events=tuple(events))


def contains_loop_sentinel(text: str, *, sentinel: str = SENTINEL) -> bool:
    """True iff ``text`` contains a loop-removal sentinel."""
    return sentinel in text


def _main() -> None:
    """Preview loops in a file without writing anything (read-only)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--input", required=True, help="OCR'd markdown file to inspect."
    )
    parser.add_argument("--min-repeats", type=int, default=DEFAULT_MIN_REPEATS)
    parser.add_argument(
        "--max-phrase-words", type=int, default=DEFAULT_MAX_PHRASE_WORDS
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level, format="%(levelname)s %(message)s")
    with open(args.input, encoding="utf-8") as f:
        markdown = f.read()

    result = clean_degeneration_loops(
        markdown,
        min_repeats=args.min_repeats,
        max_phrase_words=args.max_phrase_words,
    )
    if not result.events:
        log.info("No degeneration loops found in %s.", args.input)
        return
    log.info("Found %d loop(s) in %s:", result.loop_count, args.input)
    for e in result.events:
        log.info(
            "  line %d: %r x%d (%d chars)",
            e.line_number,
            e.phrase,
            e.repeats,
            e.removed_chars,
        )


if __name__ == "__main__":
    _main()
