"""Inter-annotator agreement for the relevance task (H3).

The headline number is **Krippendorff's α (ordinal)** over the anchor — the
units graded by 2+ teachers — which extends naturally to any number of raters
and tolerates the missing data of an overlap design. We delegate α to the
`krippendorff` package and keep light 2-rater readouts (exact / adjacent /
binary agreement, Cohen's κ, quadratic-weighted κ) for the pilot and the
2-rater anchor.

A "unit" is a (query, chunk) pair; a "rater" is a teacher code; the value is the
0-3 relevance label.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

import krippendorff
import numpy as np

Record = tuple[str, str, int]  # (unit_id, rater_id, value)


def _by_unit(records: Iterable[Record]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(dict)
    for unit, rater, value in records:
        out[unit][rater] = value
    return out


def krippendorff_alpha(
    records: Iterable[Record], level_of_measurement: str = "ordinal"
) -> float:
    """Krippendorff's α over units with ≥2 ratings. NaN if none qualify.

    Units rated by a single teacher (the coverage tier) carry no agreement
    information and are dropped before α is computed.
    """
    by_unit = _by_unit(records)
    multi = {u: r for u, r in by_unit.items() if len(r) >= 2}
    if len(multi) < 1:
        return float("nan")
    units = sorted(multi)
    raters = sorted({r for ratings in multi.values() for r in ratings})
    matrix = np.full((len(raters), len(units)), np.nan)
    ridx = {r: i for i, r in enumerate(raters)}
    for j, u in enumerate(units):
        for r, v in multi[u].items():
            matrix[ridx[r], j] = v
    return float(
        krippendorff.alpha(
            reliability_data=matrix, level_of_measurement=level_of_measurement
        )
    )


def _two_rater_pairs(records: Iterable[Record]) -> list[tuple[int, int]]:
    """For units rated by exactly two raters, the (rater_a, rater_b) score pair.

    Rater order within a unit is fixed by sorted rater id, so the result is
    deterministic. Units with ≠2 raters are skipped.
    """
    pairs = []
    for ratings in _by_unit(records).values():
        if len(ratings) == 2:
            (_, a), (_, b) = sorted(ratings.items())
            pairs.append((a, b))
    return pairs


def cohen_kappa(pairs: list[tuple[int, int]], categories: list[int]) -> float:
    """Unweighted Cohen's κ for two raters over discrete categories."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    obs = [[0] * k for _ in range(k)]
    for a, b in pairs:
        obs[idx[a]][idx[b]] += 1
    po = sum(obs[i][i] for i in range(k)) / n
    row = [sum(obs[i]) / n for i in range(k)]
    col = [sum(obs[i][j] for i in range(k)) / n for j in range(k)]
    pe = sum(row[i] * col[i] for i in range(k))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def weighted_kappa(pairs: list[tuple[int, int]], categories: list[int]) -> float:
    """Quadratic-weighted Cohen's κ over an ordinal scale."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    span2 = (len(categories) - 1) ** 2
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    w = [[((i - j) ** 2) / span2 for j in range(k)] for i in range(k)]
    obs = [[0.0] * k for _ in range(k)]
    for a, b in pairs:
        obs[idx[a]][idx[b]] += 1
    row = [sum(obs[i]) for i in range(k)]
    col = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    num = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k))
    den = sum(w[i][j] * row[i] * col[j] / n for i in range(k) for j in range(k))
    return 1.0 if den == 0 else 1 - num / den


def summarize(records: Iterable[Record], categories: list[int] = [0, 1, 2, 3]) -> dict:
    """All agreement stats for an overlap-design label set."""
    records = list(records)
    by_unit = _by_unit(records)
    multi = {u: r for u, r in by_unit.items() if len(r) >= 2}
    out: dict = {
        "n_units": len(by_unit),
        "n_units_multi_rated": len(multi),
        "n_raters": len({r for _, r, _ in records}),
        "krippendorff_alpha_ordinal": krippendorff_alpha(records, "ordinal"),
        "krippendorff_alpha_nominal": krippendorff_alpha(records, "nominal"),
    }
    pairs = _two_rater_pairs(records)
    if pairs:
        exact = sum(a == b for a, b in pairs) / len(pairs)
        adjacent = sum(abs(a - b) <= 1 for a, b in pairs) / len(pairs)
        binp = [(int(a >= 2), int(b >= 2)) for a, b in pairs]
        out["two_rater"] = {
            "n_pairs": len(pairs),
            "exact": exact,
            "adjacent": adjacent,
            "binary_relevant": sum(a == b for a, b in binp) / len(binp),
            "cohen_kappa_binary": cohen_kappa(binp, [0, 1]),
            "weighted_kappa": weighted_kappa(pairs, categories),
            "abs_diff_dist": dict(sorted(Counter(abs(a - b) for a, b in pairs).items())),
        }
    return out
