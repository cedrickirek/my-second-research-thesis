from src.corpus import filters
from src.ocr.clean import SENTINEL


def test_mismatched_delimiters_detects_odd_dollar_count():
    assert filters.mismatched_delimiters("foo $x + 1 bar")
    assert not filters.mismatched_delimiters("foo $x + 1$ bar")


def test_mismatched_delimiters_handles_block():
    # $$...$$ contributes 4 dollars → even → no flag.
    assert not filters.mismatched_delimiters(r"prelude $$a = b$$ epilogue")


def test_unbalanced_braces_flag():
    assert filters.unbalanced_braces([r"\frac{a}{b"])
    assert not filters.unbalanced_braces([r"\frac{a}{b}"])


def test_equations_without_prose_flag_when_only_latex():
    text = "$a$ $b$ $c$ $d$"
    eqs = ["a", "b", "c", "d"]
    assert filters.equations_without_prose(text, eqs)


def test_equations_without_prose_passes_with_prose():
    text = (
        "Soit a, b et c trois entiers relatifs non nuls. "
        "On dit que a divise b s'il existe k tel que $a = kb$."
    )
    assert not filters.equations_without_prose(text, ["a = kb"])


def test_suspicious_short_equation_fires_on_tiny_eq():
    assert filters.suspicious_short_equation(["."])
    assert filters.suspicious_short_equation(["x", "very long equation here"])
    assert not filters.suspicious_short_equation(["x + 1"])


def test_layout_artefact_in_equation_catches_bullet_bleed():
    # Reproduces the worst-case marker bleed observed in the validation run.
    assert filters.layout_artefact_in_equation([r"\bullet - 81 \equiv 0 [9]"])
    assert filters.layout_artefact_in_equation([r"-Si\ A = A'"])
    assert not filters.layout_artefact_in_equation([r"a + b = c"])


def test_hallucination_flags_is_stable_and_named():
    clean = (
        "Soit a et b deux entiers relatifs non nuls. Si b divise a "
        "alors il existe un entier q tel que $a = bq$."
    )
    assert filters.hallucination_flags(clean) == ()

    bad = "$x"  # single delimiter
    flags = filters.hallucination_flags(bad)
    assert "mismatched_delimiters" in flags


def test_clean_chunk_emits_no_flags():
    text = (
        "Soit a et b deux entiers relatifs. On dit que a est un multiple "
        "de b s'il existe un entier relatif k tel que $a = kb$."
    )
    assert filters.hallucination_flags(text) == ()


def test_ocr_degeneration_loop_detects_sentinel():
    assert filters.ocr_degeneration_loop(f"Texte {SENTINEL} suite")
    assert not filters.ocr_degeneration_loop("Texte sans artefact de boucle")


def test_hallucination_flags_includes_loop_flag():
    flags = filters.hallucination_flags(f"# Exercices {SENTINEL}")
    assert "ocr_degeneration_loop" in flags
