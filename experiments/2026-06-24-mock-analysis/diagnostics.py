"""Agreement diagnostics for the mock analysis (no retrieval stack needed).

Explains the headline Krippendorff alpha: label distribution, per-rater
behaviour, leave-one-out alpha (who drags agreement down), and the clean
pairwise weighted kappa on the two full-overlap doublons (same assignment file
graded by two different people).

    uv run python experiments/2026-06-24-mock-analysis/diagnostics.py \
        --labels "experiments/annotated/clean/*.jsonl"
"""

from __future__ import annotations

import argparse
import glob
from collections import Counter, defaultdict
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.agreement import krippendorff_alpha, weighted_kappa  # noqa: E402
from src.eval.relevance.qrels import agreement_records, load_labels  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    args = ap.parse_args()

    paths = [Path(p) for p in glob.glob(args.labels)]
    labels = load_labels(paths)
    recs = agreement_records(labels)  # (pair_id, rater, value)

    # --- overall label distribution ---
    dist = Counter(v for _, _, v in recs)
    n = sum(dist.values())
    print(f"\n=== Label distribution (n={n}) ===")
    for v in (0, 1, 2, 3):
        c = dist.get(v, 0)
        print(f"  rel={v}: {c:5d}  {c/n:6.1%}")

    # --- per-rater behaviour ---
    by_rater: dict[str, list[int]] = defaultdict(list)
    for _, r, v in recs:
        by_rater[r].append(v)
    print("\n=== Per-rater (mean rel, %relevant>=2, label mix) ===")
    print(f"  {'rater':<6}{'n':>5}{'mean':>7}{'%rel>=2':>9}   dist[0,1,2,3]")
    for r in sorted(by_rater):
        xs = by_rater[r]
        d = Counter(xs)
        mean = sum(xs) / len(xs)
        relshare = sum(x >= 2 for x in xs) / len(xs)
        print(f"  {r:<6}{len(xs):>5}{mean:>7.2f}{relshare:>8.0%}   "
              f"[{d.get(0,0)},{d.get(1,0)},{d.get(2,0)},{d.get(3,0)}]")

    # --- leave-one-out alpha (ordinal) ---
    full = krippendorff_alpha(recs, "ordinal")
    print(f"\n=== Leave-one-out alpha (full ordinal alpha = {full:.3f}) ===")
    raters = sorted(by_rater)
    loo = []
    for r in raters:
        sub = [(u, rr, v) for (u, rr, v) in recs if rr != r]
        a = krippendorff_alpha(sub, "ordinal")
        loo.append((a, r))
        print(f"  without {r}: alpha = {a:.3f}  (delta {a-full:+.3f})")
    best = max(loo)
    print(f"  -> removing {best[1]} most improves alpha ({best[0]:.3f})")

    # --- clean pairwise on the full-overlap doublons ---
    # same assignment file graded by two different people
    by_pair_raters: dict[str, dict[str, int]] = defaultdict(dict)
    for u, r, v in recs:
        by_pair_raters[u][r] = v
    print("\n=== Full-overlap doublon pairs (clean 2-rater) ===")
    for a_id, b_id in (("T03", "T14"), ("T08", "T11")):
        pairs = [
            (rr[a_id], rr[b_id])
            for rr in by_pair_raters.values()
            if a_id in rr and b_id in rr
        ]
        if not pairs:
            print(f"  {a_id} vs {b_id}: no shared pairs")
            continue
        exact = sum(x == y for x, y in pairs) / len(pairs)
        adj = sum(abs(x - y) <= 1 for x, y in pairs) / len(pairs)
        wk = weighted_kappa(pairs, [0, 1, 2, 3])
        print(f"  {a_id} vs {b_id}: n={len(pairs)}  exact={exact:.0%}  "
              f"adjacent={adj:.0%}  weighted_kappa={wk:.3f}")


if __name__ == "__main__":
    main()
