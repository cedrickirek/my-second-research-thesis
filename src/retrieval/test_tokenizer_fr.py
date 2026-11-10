"""Unit tests for the French BM25 tokenizer.

Run: uv run pytest src/retrieval/ -q
"""

from src.retrieval.tokenizer_fr import FrenchTokenizer

# Load the spaCy model once per module (loading is the slow part).
_TOK = FrenchTokenizer(fold_accents=True)
_TOK_NO_FOLD = FrenchTokenizer(fold_accents=False)


def test_elision_clitic_is_dropped():
    # "l'" is a stopword elision; it must not leak through as a bare "l".
    toks = _TOK.tokenize("L'élève")
    assert "l" not in toks
    assert "eleve" in toks  # élève -> lowercased + accent-folded


def test_single_letter_variable_is_kept():
    # "a" is a French stopword (verb avoir) but here it is a math variable.
    toks = _TOK.tokenize("a = kb")
    assert "a" in toks
    assert "kb" in toks


def test_symbols_are_dropped():
    assert "=" not in _TOK.tokenize("a = b")


def test_multichar_stopwords_are_dropped():
    toks = _TOK.tokenize("le théorème de la divisibilité")
    assert "le" not in toks
    assert "de" not in toks
    assert "la" not in toks
    assert "theoreme" in toks
    assert "divisibilite" in toks


def test_accent_folding_on_by_default():
    assert _TOK.tokenize("théorème") == ["theoreme"]


def test_accent_folding_can_be_disabled():
    assert _TOK_NO_FOLD.tokenize("théorème") == ["théorème"]


def test_empty_string_returns_empty_list():
    assert _TOK.tokenize("") == []
