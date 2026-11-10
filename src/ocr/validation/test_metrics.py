from src.ocr.validation import metrics


def test_extract_inline_equation():
    assert metrics.extract_equations("foo $x+1$ bar") == ["x+1"]


def test_extract_block_equation():
    assert metrics.extract_equations(r"foo $$\frac{a}{b}$$ bar") == [r"\frac{a}{b}"]


def test_extract_mixed_in_order():
    text = r"inline $a$ then block $$b$$ then inline $c$"
    assert metrics.extract_equations(text) == ["a", "b", "c"]


def test_block_is_not_double_counted_as_two_inlines():
    # The previous notebook regex matched $$xy$$ both as a block and as two
    # inline equations. Guard against that regression.
    assert metrics.extract_equations("$$xy$$") == ["xy"]


def test_normalize_latex_strips_whitespace():
    assert metrics.normalize_latex("a + b") == "a+b"


def test_normalize_latex_collapses_leq_to_le():
    assert metrics.normalize_latex(r"x \leq y") == r"x\ley"


def test_normalize_latex_collapses_overrightarrow_to_vec():
    assert metrics.normalize_latex(r"\overrightarrow{u}") == r"\vec{u}"
    assert metrics.normalize_latex(r"\overrightarrow{AB}") == r"\vec{AB}"


def test_similarity_identical_strings():
    assert metrics.similarity("abc", "abc") == 1.0


def test_similarity_completely_different():
    assert metrics.similarity("abc", "xyz") == 0.0


def test_normalize_prose_drops_equations_and_headers():
    text = "# Title\n\nThis is $x$ a test."
    out = metrics.normalize_prose(text)
    assert "Title" in out
    assert "test" in out
    assert "$" not in out
    assert "#" not in out


def test_align_equations_perfect_match():
    a = metrics.align_equations(["a", "b", "c"], ["a", "b", "c"])
    assert [pair[:2] for pair in a.matched] == [(0, 0), (1, 1), (2, 2)]
    assert a.unmatched_gt == []
    assert a.unmatched_pred == []


def test_align_equations_with_missing_in_pred():
    a = metrics.align_equations(["a", "b", "c"], ["a", "c"])
    assert [pair[:2] for pair in a.matched] == [(0, 0), (2, 1)]
    assert a.unmatched_gt == [1]
    assert a.unmatched_pred == []


def test_align_equations_with_hallucination():
    a = metrics.align_equations(["a", "c"], ["a", "b", "c"])
    assert [pair[:2] for pair in a.matched] == [(0, 0), (1, 2)]
    assert a.unmatched_gt == []
    assert a.unmatched_pred == [1]


def test_low_similarity_pair_is_demoted_to_unmatched():
    a = metrics.align_equations(["hello"], ["xxxxx"], min_match_similarity=0.3)
    assert a.matched == []
    assert a.unmatched_gt == [0]
    assert a.unmatched_pred == [0]
