"""Tests for the OCR degeneration-loop cleaner.

The cleaner has two jobs that pull in opposite directions: it must remove
the real vision-model loops seen in the 2026-06-09 trial, and it must never
touch legitimate math markdown (tables, derivations, repeated variables).
The tests below pin both sides, plus the structural guarantees the
downstream chunker relies on (verbatim preservation of non-loop lines,
sentinel placement, idempotence).
"""

from __future__ import annotations

from src.ocr.clean import (
    SENTINEL,
    clean_degeneration_loops,
    contains_loop_sentinel,
)


def test_removes_real_three_word_loop():
    # The 256_ciam_tc failure mode: "of the latter" x145 to a token ceiling.
    line = "# Fonction " + "of the latter " * 40
    result = clean_degeneration_loops(line)
    assert result.loop_count == 1
    event = result.events[0]
    assert event.phrase == "of the latter"
    assert event.repeats >= 40
    assert SENTINEL in result.text
    # The loop body itself is gone; the real prefix survives.
    assert "of the latter of the latter" not in result.text
    assert result.text.startswith("# Fonction")


def test_preserves_recoverable_heading_prefix():
    # The 56_ciam_tc failure mode: a real heading with a loop appended.
    line = "## Exercices " + "the control of " * 45
    result = clean_degeneration_loops(line)
    assert result.loop_count == 1
    # "## Exercices" must survive so the chunker still classifies the heading.
    assert result.text.startswith("## Exercices")
    assert SENTINEL in result.text


def test_single_word_loop_is_caught():
    line = "Texte normal " + "blabla " * 30
    result = clean_degeneration_loops(line)
    assert result.loop_count == 1
    assert result.events[0].phrase == "blabla"
    assert SENTINEL in result.text


def test_short_markdown_table_row_untouched():
    line = "| n     | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |"
    result = clean_degeneration_loops(line)
    assert result.events == ()
    assert result.text == line  # byte-for-byte


def test_long_table_row_untouched_by_consecutive_logic():
    # 24+ words so the length guard does NOT save it; only the
    # consecutive-repetition logic does. Distinct cell values => no run.
    cells = " | ".join(str(v) for v in range(20))
    line = f"| label | {cells} |"
    result = clean_degeneration_loops(line)
    assert result.events == ()
    assert result.text == line


def test_repeated_numeric_cells_not_treated_as_loop():
    # A pathological row of identical cells repeats "| 0" consecutively, but
    # the phrase is non-wordy, so the wordy guard must spare it verbatim.
    line = "| " + "0 | " * 40
    result = clean_degeneration_loops(line)
    assert result.events == ()
    assert result.text == line


def test_repeated_math_variable_in_derivation_untouched():
    line = "On a : $g(x) = 2 \\sin x \\cos x$ et $x$ varie, donc $x$ puis $x$ encore $x$."
    result = clean_degeneration_loops(line)
    assert result.events == ()
    assert result.text == line


def test_below_threshold_repetition_untouched():
    # 10 consecutive repeats is below the default threshold of 20; the
    # validation sweep reports these, the cleaner does not remove them.
    line = "intro " + "of the latter " * 10
    result = clean_degeneration_loops(line)
    assert result.events == ()
    assert result.text == line


def test_normal_french_prose_untouched():
    line = (
        "Pour tous entiers naturels a et b, a + b et a fois b sont des "
        "entiers naturels, et l'addition est une loi de composition interne."
    )
    result = clean_degeneration_loops(line)
    assert result.events == ()
    assert result.text == line


def test_non_loop_lines_preserved_verbatim_including_whitespace():
    doc = "## Titre\n\nUne   phrase   avec   des   espaces.\n\n| a | b |\n"
    result = clean_degeneration_loops(doc)
    assert result.events == ()
    assert result.text == doc  # exact round-trip, no reflow


def test_multiple_loops_on_different_lines():
    doc = (
        "# A\n"
        + "alpha beta " * 25
        + "\n"
        + "middle line stays\n"
        + "gamma delta " * 30
        + "\n"
    )
    result = clean_degeneration_loops(doc)
    assert result.loop_count == 2
    line_numbers = sorted(e.line_number for e in result.events)
    assert line_numbers == [2, 4]
    assert "middle line stays" in result.text


def test_idempotent():
    doc = "# H " + "of the latter " * 50 + "\nplain line\n"
    once = clean_degeneration_loops(doc).text
    twice = clean_degeneration_loops(once).text
    assert once == twice
    # And a second pass finds nothing new to remove.
    assert clean_degeneration_loops(once).loop_count == 0


def test_clean_document_returns_input_unchanged():
    doc = "# Définition\n\nUn entier $n$ est pair s'il existe $k$ tel que $n = 2k$.\n"
    result = clean_degeneration_loops(doc)
    assert result.events == ()
    assert result.text == doc
    assert result.removed_chars == 0


def test_removed_chars_accounting():
    unit = "of the latter "
    line = "x " + unit * 30
    result = clean_degeneration_loops(line)
    # removed_chars counts the excised run; it should be most of the line.
    assert result.removed_chars > 0
    assert result.removed_chars >= len((unit * 30).strip()) - len(unit)


def test_sentinel_detector():
    assert contains_loop_sentinel(f"abc {SENTINEL} def") is True
    assert contains_loop_sentinel("nothing here") is False


def test_sentinel_contains_no_dollar_sign():
    # Guards the invariant that a sentinel can never create/break a LaTeX
    # delimiter when it lands inside a chunk.
    assert "$" not in SENTINEL
