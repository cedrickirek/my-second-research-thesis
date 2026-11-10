"""H4 analysis: does grounding close the frontier-vs-SLM gap?

Reads judged.jsonl (Gemini 2.5 Pro scores, 4 criteria x 1-5, for the 2x2
{grounded,ungrounded} x {frontier,slm} over N queries) and answers H4 with a
paired bootstrap over queries -- the same resampling approach used for H1/H2, so
the inferential method is consistent across the thesis.

Operationalization
------------------
For each query q and criterion c, let s[model, grounding] be the judge score.

  gap_grounded(q,c)   = frontier_grounded   - slm_grounded
  gap_ungrounded(q,c) = frontier_ungrounded - slm_ungrounded

H4 ("grounding closes the gap") predicts the gap SHRINKS with grounding:

  delta_gap(q,c) = gap_ungrounded - gap_grounded      ( > 0 supports H4 )

We also report the mechanism -- how much grounding lifts each model:

  slm_lift(q,c)      = slm_grounded      - slm_ungrounded
  frontier_lift(q,c) = frontier_grounded - frontier_ungrounded

Reported per criterion AND on the 4-criterion mean. 95% CIs by resampling the
QUERIES with replacement (B=10000, seed=42); a point estimate whose CI excludes
0 is the bootstrap analogue of significance. P(>0) is the bootstrap mass above 0.

H4 is EXPLORATORY: the Gemini judge is uncalibrated for response grading
(teacher response-grades were not collected in time). Treat CIs as descriptive
of the judged scores, not as a validated human-aligned effect.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
JUDGED = SCRIPT_DIR / "judged.jsonl"
OUT_JSON = SCRIPT_DIR / "h4_results.json"

CRITERIA = ("factual_accuracy", "curriculum_alignment", "pedagogical_quality", "language_register")
B = 10000
SEED = 42


def load() -> dict[str, dict[tuple[str, str], dict]]:
    """Index judged rows by query_id -> (model_role, grounding) -> scores+mean."""
    by_q: dict[str, dict[tuple[str, str], dict]] = {}
    for line in JUDGED.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        cell = (r["model_role"], r["grounding"])
        by_q.setdefault(r["query_id"], {})[cell] = {
            "scores": r["scores"],
            "mean": r["judge_mean"],
        }
    return by_q


def complete_queries(by_q: dict) -> list[str]:
    """Keep only queries with all 4 cells present (a complete 2x2)."""
    need = {("frontier", "grounded"), ("frontier", "ungrounded"),
            ("slm", "grounded"), ("slm", "ungrounded")}
    return sorted(q for q, cells in by_q.items() if need <= set(cells))


def metric_vector(by_q: dict, queries: list[str], crit: str | None) -> dict[str, np.ndarray]:
    """Per-query arrays for each derived metric, on one criterion or the 4-mean."""
    def s(q, model, grounding):
        cell = by_q[q][(model, grounding)]
        return cell["mean"] if crit is None else cell["scores"][crit]

    fg = np.array([s(q, "frontier", "grounded") for q in queries], float)
    fu = np.array([s(q, "frontier", "ungrounded") for q in queries], float)
    sg = np.array([s(q, "slm", "grounded") for q in queries], float)
    su = np.array([s(q, "slm", "ungrounded") for q in queries], float)
    return {
        "gap_grounded": fg - sg,
        "gap_ungrounded": fu - su,
        "delta_gap": (fu - su) - (fg - sg),  # >0 => grounding closes the gap
        "slm_lift": sg - su,
        "frontier_lift": fg - fu,
        "_means": {"fg": fg.mean(), "fu": fu.mean(), "sg": sg.mean(), "su": su.mean()},
    }


def boot_ci(per_query: np.ndarray, rng: np.random.Generator) -> dict:
    """Mean + 95% CI + P(>0) by resampling queries with replacement."""
    n = len(per_query)
    idx = rng.integers(0, n, size=(B, n))
    boots = per_query[idx].mean(axis=1)
    return {
        "mean": float(per_query.mean()),
        "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
        "p_gt_0": float((boots > 0).mean()),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    by_q = load()
    queries = complete_queries(by_q)
    print(f"complete 2x2 queries: {len(queries)}")
    rng = np.random.default_rng(SEED)

    results: dict = {"n_queries": len(queries), "judge": "gemini-2.5-pro",
                     "note": "EXPLORATORY: uncalibrated response judge", "by_criterion": {}}

    for crit in (None,) + CRITERIA:
        key = "mean_4crit" if crit is None else crit
        v = metric_vector(by_q, queries, crit)
        block = {"raw_means": v.pop("_means")}
        for metric in ("gap_ungrounded", "gap_grounded", "delta_gap", "slm_lift", "frontier_lift"):
            block[metric] = boot_ci(v[metric], rng)
        results["by_criterion"][key] = block

    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # Readable summary
    def fmt(d):
        lo, hi = d["ci95"]
        star = "*" if (lo > 0 or hi < 0) else " "
        return f"{d['mean']:+.3f} [{lo:+.3f},{hi:+.3f}] P>0={d['p_gt_0']:.3f}{star}"

    print("\n" + "=" * 78)
    print("H4: does grounding close the frontier-vs-SLM gap?  (* = 95% CI excludes 0)")
    print("=" * 78)
    for key, b in results["by_criterion"].items():
        m = b["raw_means"]
        print(f"\n[{key}]  raw means: F_grd={m['fg']:.2f} F_ung={m['fu']:.2f} "
              f"S_grd={m['sg']:.2f} S_ung={m['su']:.2f}")
        print(f"   gap ungrounded : {fmt(b['gap_ungrounded'])}")
        print(f"   gap grounded   : {fmt(b['gap_grounded'])}")
        print(f"   DELTA gap (H4) : {fmt(b['delta_gap'])}   <- >0 means grounding closes gap")
        print(f"   SLM lift       : {fmt(b['slm_lift'])}")
        print(f"   frontier lift  : {fmt(b['frontier_lift'])}")
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    main()
