"""Tests for the agreement module. Run: uv run pytest src/eval/relevance/test_agreement.py"""

import math

from src.eval.relevance.agreement import (
    cohen_kappa,
    krippendorff_alpha,
    summarize,
    weighted_kappa,
)


def test_perfect_agreement_alpha_is_one():
    # Two raters, identical labels on every unit -> alpha = 1.
    records = []
    for u, v in [("p1", 3), ("p2", 0), ("p3", 2), ("p4", 1)]:
        records.append((u, "T01", v))
        records.append((u, "T02", v))
    assert math.isclose(krippendorff_alpha(records, "ordinal"), 1.0, abs_tol=1e-9)


def test_single_rated_units_ignored_returns_nan():
    # No unit has 2+ raters -> alpha undefined.
    records = [("p1", "T01", 2), ("p2", "T02", 3)]
    assert math.isnan(krippendorff_alpha(records))


def test_ordinal_rewards_near_misses_over_nominal():
    # Raters off by 1 on ordinal data: ordinal alpha should exceed nominal alpha
    # (a 2-vs-3 disagreement is small on an ordinal scale, total on a nominal one).
    records = []
    for u, (a, b) in {
        "p1": (3, 2), "p2": (2, 3), "p3": (0, 1), "p4": (1, 0),
        "p5": (3, 3), "p6": (0, 0), "p7": (2, 2), "p8": (1, 1),
    }.items():
        records.append((u, "T01", a))
        records.append((u, "T02", b))
    a_ord = krippendorff_alpha(records, "ordinal")
    a_nom = krippendorff_alpha(records, "nominal")
    assert a_ord > a_nom


def test_weighted_kappa_perfect_and_ordering():
    cats = [0, 1, 2, 3]
    perfect = [(0, 0), (1, 1), (2, 2), (3, 3)]
    assert math.isclose(weighted_kappa(perfect, cats), 1.0, abs_tol=1e-9)
    # An off-by-one set scores higher on weighted than unweighted kappa.
    near = [(3, 2), (2, 3), (1, 1), (0, 0), (2, 2), (3, 3)]
    assert weighted_kappa(near, cats) > cohen_kappa(near, cats)


def test_summarize_shapes_and_two_rater_block():
    records = []
    for u, (a, b) in {"p1": (3, 3), "p2": (2, 1), "p3": (0, 0)}.items():
        records.append((u, "T01", a))
        records.append((u, "T02", b))
    records.append(("p4", "T03", 2))  # single-rated coverage unit
    s = summarize(records)
    assert s["n_units"] == 4
    assert s["n_units_multi_rated"] == 3
    assert s["two_rater"]["n_pairs"] == 3
    assert 0.0 <= s["two_rater"]["adjacent"] <= 1.0
