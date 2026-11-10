from src.corpus.chunking import chunk_markdown
from src.corpus.metadata import ContentType


_SOURCE = "CIAM Terminale C, Chapitre 2"


def _chunk(md: str):
    return chunk_markdown(
        md, subject="mathematics", level="Terminale C", source=_SOURCE
    )


def test_numbered_heading_does_not_emit_a_chunk():
    md = "# 2 Divisibilité dans Z\n\n# 2.1. Multiples et diviseurs\n"
    assert _chunk(md) == []


def test_definition_heading_classifies_as_definition():
    md = (
        "# 2 Divisibilité dans Z\n\n"
        "# 2.1. Multiples et diviseurs\n\n"
        "# Définition\n\nSoit a et b deux entiers relatifs. "
        "$a = kb$ pour un certain k.\n"
    )
    chunks = _chunk(md)
    assert len(chunks) == 1
    assert chunks[0].metadata.content_type == ContentType.DEFINITION
    assert "Soit a et b" in chunks[0].text


def test_property_and_demonstration_split_into_two_chunks():
    md = (
        "# 2.1. Multiples et diviseurs\n\n"
        "# Propriété 1\n\nSoit a et b deux entiers relatifs non nuls. "
        "Si b divise a, alors $|b| \\le |a|$.\n\n"
        "# Démonstration\n\nSi b divise a, alors il existe q tel que "
        "$a = bq$. Donc $|b| \\le |a|$.\n"
    )
    chunks = _chunk(md)
    assert [c.metadata.content_type for c in chunks] == [
        ContentType.THEOREM,
        ContentType.PROOF,
    ]


def test_section_path_tracks_curriculum_hierarchy():
    md = (
        "# 2 Divisibilité dans Z\n\n"
        "# 2.1. Multiples et diviseurs\n\n"
        "# Définition\n\nbody one\n\n"
        "# 2.2. Congruence modulo n\n\n"
        "# Définition\n\nbody two\n"
    )
    chunks = _chunk(md)
    assert chunks[0].metadata.section_path == (
        "Divisibilité dans Z",
        "Multiples et diviseurs",
    )
    assert chunks[1].metadata.section_path == (
        "Divisibilité dans Z",
        "Congruence modulo n",
    )
    assert chunks[1].metadata.topic.endswith("Congruence modulo n")


def test_remark_classification():
    md = "# 2.1. Foo\n\n# Remarque\n\nNote that $a \\equiv 0$ means a is a multiple.\n"
    chunks = _chunk(md)
    assert chunks[0].metadata.content_type == ContentType.REMARK


def test_example_classification():
    md = "# 2.1. Foo\n\n# Exemples\n\n• On a $143 = 11 \\times 13$.\n"
    chunks = _chunk(md)
    assert chunks[0].metadata.content_type == ContentType.EXAMPLE


def test_unknown_heading_falls_back_to_theory():
    md = "# 2.1. Foo\n\n# Convention\n\nDans tout ce qui suit, n désigne un entier naturel.\n"
    chunks = _chunk(md)
    assert chunks[0].metadata.content_type == ContentType.THEORY


def test_dropped_figure_is_tagged():
    md = (
        "# 2.1. Foo\n\n# Définition\n\n"
        "Voici la situation:\n\n![](_page_10_Figure_35.jpeg)\n\n"
        "On voit que $A = B$.\n"
    )
    chunks = _chunk(md)
    assert chunks[0].metadata.has_dropped_figure is True
    # The figure reference itself should be stripped from the chunk text.
    assert "_page_10_Figure" not in chunks[0].text


def test_chunk_counts_equations_and_chars():
    md = "# 2.1. Foo\n\n# Définition\n\nOn a $a = kb$ et $b \\neq 0$.\n"
    chunks = _chunk(md)
    assert chunks[0].metadata.equation_count == 2
    assert chunks[0].metadata.char_count > 0


def test_hallucination_flag_propagates_to_metadata():
    md = "# 2.1. Foo\n\n# Exemples\n\nx $a + b foo\n"  # mismatched $
    chunks = _chunk(md)
    assert "mismatched_delimiters" in chunks[0].metadata.hallucination_flags


def test_metadata_uses_provided_source_and_level():
    md = "# 2.1. Foo\n\n# Définition\n\nbody\n"
    chunks = _chunk(md)
    m = chunks[0].metadata
    assert m.source == _SOURCE
    assert m.level == "Terminale C"
    assert m.subject == "mathematics"


def test_markdown_emphasis_in_heading_does_not_block_classification():
    md = "# 2.1. Foo\n\n# **Propriété**\n\nSi b divise a alors $|b| \\le |a|$.\n"
    chunks = _chunk(md)
    assert chunks[0].metadata.content_type == ContentType.THEOREM


def test_topic_string_is_section_path_joined():
    md = "# 2 Divisibilité dans Z\n\n# 2.1. Multiples\n\n# Définition\n\nbody\n"
    chunks = _chunk(md)
    assert chunks[0].metadata.topic == "Divisibilité dans Z > Multiples"


# --- option A (2026-06-10): richer worked-example cues + OCR drop-cap tolerance


def test_resolution_heading_classifies_as_example():
    md = "# 2.1. Foo\n\n# Résolution de l'équation (1)\n\nOn a $x = 2$.\n"
    assert _chunk(md)[0].metadata.content_type == ContentType.EXAMPLE


def test_etude_de_la_fonction_classifies_as_example():
    md = "# 2.1. Foo\n\n# Étude de la fonction $f: x \\mapsto x^2$\n\nbody\n"
    assert _chunk(md)[0].metadata.content_type == ContentType.EXAMPLE


def test_elided_article_before_etude_classifies_as_example():
    md = "# 2.1. Foo\n\n# L'Étude d'une branche infinie\n\nbody\n"
    assert _chunk(md)[0].metadata.content_type == ContentType.EXAMPLE


def test_imperative_worked_headings_classify_as_example():
    for h in (
        "Calculer les racines carrées de 3 - 4i.",
        "Résoudre dans R les équations suivantes.",
        "Déterminer l'ensemble de définition",
    ):
        md = f"# 2.1. Foo\n\n# {h}\n\nbody\n"
        assert _chunk(md)[0].metadata.content_type == ContentType.EXAMPLE, h


def test_etude_algebrique_is_not_swept_into_example():
    # A topic-style "Étude …" with no "de"/"d'" must stay theory, not pollute
    # the example slot — the precision guard for the new cues.
    md = "# 2.1. Foo\n\n# Étude algébrique\n\nbody\n"
    assert _chunk(md)[0].metadata.content_type == ContentType.THEORY


def test_ocr_dropcap_demonstration_classifies_as_proof():
    # marker lost the decorative initial: "Démonstration" -> "émonstration".
    md = "# 2.1. Foo\n\n# émonstration\n\nSi b divise a alors $a = bq$.\n"
    assert _chunk(md)[0].metadata.content_type == ContentType.PROOF


def test_ocr_dropcap_solution_and_exercice():
    sol = _chunk("# 2.1. Foo\n\n# olution\n\nOn a $x = 1$.\n")
    assert sol[0].metadata.content_type == ContentType.SOLUTION
    exo = _chunk("# 2.1. Foo\n\n# xercices\n\nÉnoncé.\n")
    assert exo[0].metadata.content_type == ContentType.EXERCISE


def test_numbered_heading_with_example_cue_is_still_a_topic():
    # A numbered heading is a curriculum topic regardless of the cue word.
    md = "# 2.1. Résolution de l'équation\n\n# Définition\n\nbody\n"
    assert [c.metadata.content_type for c in _chunk(md)] == [ContentType.DEFINITION]
