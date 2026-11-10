"""SECONDARY H3 validation: assessor↔panel agreement vs the human-panel ceiling.

The primary H3 evidence is *ranking* agreement (analyze.py on the LLM qrels). This
script is the per-item secondary: how well does the calibrated assessor agree with
the human panel, and how does that compare to the panel's own internal ceiling
(α = 0.464, the mixed 2-teacher/8-student anchor)?

Construction — one collapsed grade per rater so the comparison is a clean 1-vs-1
over every shared (query, chunk) pair:
  * PANEL grade  = round-half-up of ALL human labels on the pair (same aggregation
                   `build_qrels` uses for the human qrels).
  * LLM grade    = round-half-up of the 2 assessor runs (LLM_run1, LLM_run2).
Then `summarize` over the (PANEL, LLM) two-rater units gives ordinal α + quadratic
κ + the 1↔2-boundary readouts (binary_relevant / cohen_kappa_binary).

We compare the resulting α against the panel↔panel ceiling reported in
`experiments/2026-06-20-dispatch-analysis/report.json` (the 0.464 anchor).

Run:
  uv run python experiments/2026-06-27-h3-assessor/assessor_vs_panel.py
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
HUMAN_REPORT = REPO_ROOT / "experiments/2026-06-20-dispatch-analysis/report.json"
OUT = HERE / "report_assessor_vs_panel.json"


def _round_half_up(x: float) -> int:
    return int(x + 0.5)


def collapse(labels: list[dict]) -> dict[str, int]:
    """One grade per pair_id = round-half-up of the mean over that pair's labels."""
    by_pair: dict[str, list[int]] = defaultdict(list)
    for la in labels:
        by_pair[la["pair_id"]].append(la["relevance"])
    return {p: _round_half_up(sum(v) / len(v)) for p, v in by_pair.items()}


def main() -> None:
    human_paths = [Path(p) for p in glob.glob(HUMAN_GLOB)]
    if not human_paths:
        raise SystemExit(f"no human label files match {HUMAN_GLOB!r}")
    panel = collapse(load_labels(human_paths))
    llm = collapse(load_labels([LLM_LABELS]))

    shared = sorted(set(panel) & set(llm))
    only_panel = set(panel) - set(llm)
    only_llm = set(llm) - set(panel)

    # Two-rater records over shared pairs: rater "PANEL" vs rater "LLM".
    records = []
    for p in shared:
        records.append((p, "PANEL", panel[p]))
        records.append((p, "LLM", llm[p]))

    agr = summarize(records)

    ceiling = json.loads(HUMAN_REPORT.read_text(encoding="utf-8"))["agreement"]

    report = {
        "n_shared_pairs": len(shared),
        "n_only_panel": len(only_panel),
        "n_only_llm": len(only_llm),
        "n_human_files": len(human_paths),
        "assessor_vs_panel": agr,
        "panel_internal_ceiling": {
            "krippendorff_alpha_ordinal": ceiling["krippendorff_alpha_ordinal"],
            "krippendorff_alpha_nominal": ceiling["krippendorff_alpha_nominal"],
            "n_units_multi_rated": ceiling["n_units_multi_rated"],
            "n_raters": ceiling["n_raters"],
            "two_rater": ceiling.get("two_rater", {}),
        },
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    a = agr
    c = report["panel_internal_ceiling"]
    print(f"\n=== Assessor vs Panel (shared pairs: {len(shared)}) ===")
    print(f"  only-panel {len(only_panel)} · only-llm {len(only_llm)}")
    print(f"  Krippendorff alpha — ordinal: {a['krippendorff_alpha_ordinal']:.3f} | "
          f"nominal: {a['krippendorff_alpha_nominal']:.3f}")
    t = a.get("two_rater", {})
    if t:
        print(f"  [2-rater] exact {t['exact']:.1%} · adjacent {t['adjacent']:.1%} · "
              f"weighted kappa {t['weighted_kappa']:.3f}")
        print(f"            binary(rel>=2) agreement {t['binary_relevant']:.1%} · "
              f"binary kappa {t['cohen_kappa_binary']:.3f}")
        print(f"            abs-diff dist {t['abs_diff_dist']}")
    print("\n=== Panel internal ceiling (anchor, human-vs-human) ===")
    print(f"  Krippendorff alpha — ordinal: {c['krippendorff_alpha_ordinal']:.3f} | "
          f"nominal: {c['krippendorff_alpha_nominal']:.3f}  "
          f"({c['n_units_multi_rated']} multi-rated, {c['n_raters']} raters)")
    print(f"\nreport -> {OUT}")


if __name__ == "__main__":
    main()
