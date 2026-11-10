from src.corpus import figures


def test_detects_marker_figure_reference():
    text = (
        "Voici la figure ci-dessous.\n\n![](_page_10_Figure_35.jpeg)\n\nSuite du texte."
    )
    assert figures.has_figure_reference(text)
    assert figures.count_figure_references(text) == 1


def test_detects_picture_variant_and_alt_text():
    text = "![diagram](_page_8_Picture_17.jpeg)"
    assert figures.has_figure_reference(text)


def test_ignores_non_marker_images():
    text = "![logo](https://example.com/logo.png)"
    assert not figures.has_figure_reference(text)


def test_strip_removes_reference_in_place():
    text = "avant ![](_page_1_Figure_2.jpeg) après"
    stripped = figures.strip_figure_references(text)
    assert "_page_" not in stripped
    assert "avant" in stripped and "après" in stripped


def test_counts_multiple_references():
    text = "![](_page_1_Figure_1.jpeg)\n\n![](_page_2_Picture_3.jpeg)"
    assert figures.count_figure_references(text) == 2
