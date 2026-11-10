"""Deeper annotation QC: structural integrity, straight-lining, and the key
question — is any annotator's file misaligned/corrupted end-to-end?

Reads each T*.jsonl in file order (one rater per file) so order-sensitive checks
(longest identical run) are meaningful. Reports, per rater:

  A. integrity   — duplicate pairs, pair_ids absent from the dispatched set,
                   query_id/chunk_id fields inconsistent with pair_id, grades
                   out of 0-3. Any non-zero count is a real data problem.
  B. effort      — grade entropy (bits) and longest run of identical consecutive
                   grades (straight-lining signal).
  C. partner agreement — over the anchor (each anchor pair = exactly 2 raters),
                   each rater's mean |grade diff| with its partners. A file that
                   is shifted/misaligned end-to-end shows UNIFORMLY high mean
                   |diff| against every partner, well above the panel mean.
  D. partner matrix — shared-anchor count and mean |diff| for each rater pair
                   (also the groundwork for later teacher/student stratification).

Run:
  uv run python experiments/2026-06-27-annotation-profile/deep_qc.py \
      --labels "experiments/annotated/T*.jsonl"
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read_file_in_order(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def valid_pair_ids(path: Path) -> set[str]:
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(json.loads(line)["pair_id"])
    return ids


def entropy(grades: list[int]) -> float:
    n = len(grades)
    if not n:
        return 0.0
    c = Counter(grades)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def longest_identical_run(grades: list[int]) -> int:
    best = run = 0
    prev = object()
    for g in grades:
        run = run + 1 if g == prev else 1
        best = max(best, run)
        prev = g
    return best


def integrity_and_effort(rater_rows: dict[str, list[dict]], valid: set[str]) -> dict:
    out: dict[str, dict] = {}
    for rater, rows in sorted(rater_rows.items()):
        pair_ids = [r["pair_id"] for r in rows]
        grades = [r.get("relevance") for r in rows]
        graded = [g for g in grades if g is not None]
        dup = {p: c for p, c in Counter(pair_ids).items() if c > 1}
        unknown = [p for p in pair_ids if p not in valid]
        inconsistent = 0
        for r in rows:
            qid, cid = r["pair_id"].split("__", 1)
            if r.get("query_id") != qid or r.get("chunk_id") != cid:
                inconsistent += 1
        out[rater] = {
            "n_rows": len(rows),
            "n_unique_pairs": len(set(pair_ids)),
            "n_duplicate_pairs": len(dup),
            "duplicate_examples": list(dup)[:5],
            "n_pair_id_not_in_dispatch": len(unknown),
            "n_field_inconsistent": inconsistent,
            "n_ungraded": len(grades) - len(graded),
            "n_out_of_range": sum(1 for g in graded if g not in (0, 1, 2, 3)),
            "grade_entropy_bits": round(entropy(graded), 3),
            "longest_identical_run": longest_identical_run(graded),
        }
    return out


def partner_agreement(rater_rows: dict[str, list[dict]]) -> dict:
    grades_by_pair: dict[str, dict[str, int]] = defaultdict(dict)
    for rater, rows in rater_rows.items():
        for r in rows:
            if r.get("relevance") is not None:
                grades_by_pair[r["pair_id"]][rater] = r["relevance"]
    anchor = {p: g for p, g in grades_by_pair.items() if len(g) == 2}

    per_rater_diffs: dict[str, list[int]] = defaultdict(list)
    pair_diffs: dict[tuple[str, str], list[int]] = defaultdict(list)
    all_diffs: list[int] = []
    for g in anchor.values():
        (ra, ga), (rb, gb) = g.items()
        d = abs(ga - gb)
        all_diffs.append(d)
        per_rater_diffs[ra].append(d)
        per_rater_diffs[rb].append(d)
        pair_diffs[tuple(sorted((ra, rb)))].append(d)

    panel_mean = sum(all_diffs) / len(all_diffs) if all_diffs else 0.0
    panel_sd = (
        math.sqrt(sum((d - panel_mean) ** 2 for d in all_diffs) / len(all_diffs))
        if all_diffs else 0.0
    )
    per_rater = {}
    for rater, ds in sorted(per_rater_diffs.items()):
        m = sum(ds) / len(ds)
        per_rater[rater] = {
            "n_anchor": len(ds),
            "mean_abs_diff": round(m, 3),
            "pct_exact": round(sum(1 for d in ds if d == 0) / len(ds), 3),
            "pct_ge2": round(sum(1 for d in ds if d >= 2) / len(ds), 3),
            # z vs panel: a uniformly-misaligned file is a high-positive outlier
            "z_vs_panel": round((m - panel_mean) / panel_sd, 2) if panel_sd else 0.0,
        }
    matrix = {
        f"{a}|{b}": {"n": len(ds), "mean_abs_diff": round(sum(ds) / len(ds), 2)}
        for (a, b), ds in sorted(pair_diffs.items())
    }
    return {
        "n_anchor_pairs": len(anchor),
        "panel_mean_abs_diff": round(panel_mean, 3),
        "panel_sd_abs_diff": round(panel_sd, 3),
        "per_rater": per_rater,
        "partner_matrix": matrix,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("--pairs", type=Path, default=REPO_ROOT / "results/relevance_pairs.jsonl")
    ap.add_argument("--out", type=Path, default=HERE / "deep_qc.json")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    paths = sorted(Path(p) for p in glob.glob(args.labels))
    if not paths:
        raise SystemExit(f"no label files match {args.labels!r}")
    rater_rows = {p.stem.split("_")[0]: read_file_in_order(p) for p in paths}
    valid = valid_pair_ids(args.pairs)

    integ = integrity_and_effort(rater_rows, valid)
    agree = partner_agreement(rater_rows)
    report = {"integrity": integ, "partner_agreement": agree}
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Structural integrity + effort (per rater) ===")
    print(f"  {'rater':<6}{'rows':>5}{'uniq':>5}{'dup':>4}{'!disp':>6}{'!field':>7}"
          f"{'ungr':>5}{'oor':>4}{'entropy':>9}{'maxrun':>8}")
    for r, d in integ.items():
        print(f"  {r:<6}{d['n_rows']:>5}{d['n_unique_pairs']:>5}{d['n_duplicate_pairs']:>4}"
              f"{d['n_pair_id_not_in_dispatch']:>6}{d['n_field_inconsistent']:>7}"
              f"{d['n_ungraded']:>5}{d['n_out_of_range']:>4}"
              f"{d['grade_entropy_bits']:>9.2f}{d['longest_identical_run']:>8}")

    pa = agree
    print(f"\n=== Partner agreement on anchor (panel mean|diff|={pa['panel_mean_abs_diff']}"
          f" sd={pa['panel_sd_abs_diff']}) ===")
    print(f"  {'rater':<6}{'nAnc':>5}{'mean|d|':>9}{'%exact':>8}{'%>=2':>7}{'z':>7}")
    for r, d in pa["per_rater"].items():
        flag = "  <-- check" if d["z_vs_panel"] >= 1.5 else ""
        print(f"  {r:<6}{d['n_anchor']:>5}{d['mean_abs_diff']:>9.2f}"
              f"{d['pct_exact']*100:>7.0f}%{d['pct_ge2']*100:>6.0f}%{d['z_vs_panel']:>7.2f}{flag}")

    print(f"\nqc -> {args.out}")


if __name__ == "__main__":
    main()
