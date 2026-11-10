"""FAIR secondary check: LLM vs each *individual* human on the anchor (155 pairs).

The headline assessor↔panel number (report_assessor_vs_panel.json, α=0.553) compares
the LLM to a *collapsed* panel grade. On the 155 double-annotated anchor pairs that
collapse averages the two humans first, which removes some human noise and tilts the
comparison in the LLM's favour relative to the human↔human ceiling (which compares two
*noisy individuals*). This script removes that advantage:

  * Restrict to the anchor = pairs graded by EXACTLY 2 humans.
  * Build LLM-vs-individual records: for each anchor pair, (pair, "HUMAN", human_i) and
    (pair, "LLM", llm) — one record-pair PER human, so the LLM is measured against each
    raw human grade, exactly as human↔human measures one raw human against another.
  * Report α / weighted κ over those LLM-vs-individual pairs and lay it beside the
    human↔human ceiling computed on the SAME 155 anchor pairs.

This is the apples-to-apples comparison: LLM-vs-individual-human vs human-vs-individual-
human, same pairs, same uncollapsed measurement.

Run:
  uv run python experiments/2026-06-27-h3-assessor/assessor_vs_individual_anchor.py
"""

from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.agreement import summarize  # noqa: E402
from src.eval.relevance.qrels import load_labels  # noqa: E402

HERE = Path(__file__).resolve().parent
HUMAN_GLOB = str(REPO_ROOT / "experiments/annotated/T*.jsonl")
LLM_LABELS = HERE / "llm_labels.jsonl"
OUT = HERE / "report_assessor_vs_individual_anchor.json"


def _round_half_up(x: float) -> int:
    return int(x + 0.5)


def main() -> None:
    human_paths = [Path(p) for p in glob.glob(HUMAN_GLOB)]
    if not human_paths:
        raise SystemExit(f"no human label files match {HUMAN_GLOB!r}")
    humans = load_labels(human_paths)
    llm = load_labels([LLM_LABELS])

    # Per-pair list of (rater, grade) for humans; collapsed LLM grade per pair.
    human_by_pair: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for la in humans:
        human_by_pair[la["pair_id"]].append((la["annotator"], la["relevance"]))
    llm_by_pair: dict[str, list[int]] = defaultdict(list)
    for la in llm:
        llm_by_pair[la["pair_id"]].append(la["relevance"])
    llm_grade = {p: _round_half_up(sum(v) / len(v)) for p, v in llm_by_pair.items()}

    # Anchor = pairs with exactly 2 *distinct* human raters.
    anchor = {
        p: graders
        for p, graders in human_by_pair.items()
        if len({r for r, _ in graders}) == 2
    }

    # --- human <-> human on the anchor (the ceiling, same 155 pairs) ---
    hh_records = []
    for p, graders in anchor.items():
        # one record per (pair, rater) — summarize pairs the two up internally
        seen = {}
        for r, g in graders:
            seen[r] = g  # if a rater somehow graded twice, last wins (shouldn't happen)
        for r, g in seen.items():
            hh_records.append((p, r, g))
    hh = summarize(hh_records)

    # --- LLM <-> each individual human on the SAME anchor pairs ---
    # For each anchor pair, emit one 2-rater unit per human: (pair#i, HUMAN, h), (pair#i, LLM, llm).
    # Suffix the unit id so each LLM-vs-human comparison is its own 2-rater unit (not a 3-rater one).
    li_records = []
    for p, graders in anchor.items():
        if p not in llm_grade:
            continue
        seen = {}
        for r, g in graders:
            seen[r] = g
        for i, (r, g) in enumerate(sorted(seen.items())):
            unit = f"{p}#h{i}"
            li_records.append((unit, "HUMAN", g))
            li_records.append((unit, "LLM", llm_grade[p]))
    li = summarize(li_records)

    report = {
        "n_anchor_pairs": len(anchor),
        "n_anchor_with_llm": sum(1 for p in anchor if p in llm_grade),
        "human_vs_human_anchor": hh,
        "llm_vs_individual_human_anchor": li,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def show(title, a):
        t = a.get("two_rater", {})
        print(f"\n=== {title} ===")
        print(f"  alpha ordinal {a['krippendorff_alpha_ordinal']:.3f} | "
              f"nominal {a['krippendorff_alpha_nominal']:.3f} | "
              f"units {a['n_units']} ({a['n_units_multi_rated']} multi-rated)")
        if t:
            print(f"  [2-rater n={t['n_pairs']}] exact {t['exact']:.1%} | "
                  f"adjacent {t['adjacent']:.1%} | weighted kappa {t['weighted_kappa']:.3f}")
            print(f"  binary(rel>=2) {t['binary_relevant']:.1%} | "
                  f"binary kappa {t['cohen_kappa_binary']:.3f} | "
                  f"abs-diff {t['abs_diff_dist']}")

    print(f"\nAnchor pairs (exactly 2 humans): {len(anchor)} "
          f"({report['n_anchor_with_llm']} also have an LLM grade)")
    show("Human vs Human (anchor ceiling)", hh)
    show("LLM vs individual Human (anchor, fair)", li)
    print(f"\nreport -> {OUT}")


if __name__ == "__main__":
    main()
