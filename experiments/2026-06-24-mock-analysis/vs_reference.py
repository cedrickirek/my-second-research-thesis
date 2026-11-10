"""Test each rater against a reference rater (default T03, judged 'spot-on').

Answers: are a rater's scores *tracking the correct answer* or effectively
independent of the item (careless / random)? For each rater, on the pairs they
share with the reference, we report agreement (exact / adjacent / weighted kappa),
signed bias (lenient = positive), gross-error rate (|diff|>=2), and the key
'tracking' signal: the rater's mean score conditioned on the reference's score.

  - A careful rater's conditional means RISE with the reference (0<1<2<3).
  - A careless 'always-high' rater's conditional means are FLAT and high.
  - A random rater agrees ~25% exact, weighted kappa ~0, flat conditional means.

    uv run python experiments/2026-06-24-mock-analysis/vs_reference.py \
        --labels "experiments/annotated/clean_dedup/*.jsonl" --ref T03
"""

from __future__ import annotations

import argparse
import glob
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.agreement import weighted_kappa  # noqa: E402
from src.eval.relevance.qrels import load_labels  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", required=True)
    ap.add_argument("--ref", default="T03")
    args = ap.parse_args()

    labels = load_labels([Path(p) for p in glob.glob(args.labels)])
    by_pair: dict[str, dict[str, int]] = defaultdict(dict)
    for la in labels:
        by_pair[la["pair_id"]][la["annotator"]] = la["relevance"]
    raters = sorted({la["annotator"] for la in labels})
    ref = args.ref

    print(f"\nReference = {ref} (treated as correct, per manual audit)\n")
    print(f"{'rater':<6}{'n':>5}{'exact':>7}{'adj<=1':>8}{'wkappa':>8}"
          f"{'bias':>7}{'gross':>7}   mean score when {ref}=0/1/2/3   read")
    print("-" * 104)

    for r in raters:
        if r == ref:
            continue
        pairs = [(by_pair[p][ref], by_pair[p][r]) for p in by_pair
                 if ref in by_pair[p] and r in by_pair[p]]
        if len(pairs) < 5:
            print(f"{r:<6}{len(pairs):>5}   (too few shared items)")
            continue
        n = len(pairs)
        exact = sum(a == b for a, b in pairs) / n
        adj = sum(abs(a - b) <= 1 for a, b in pairs) / n
        wk = weighted_kappa([(a, b) for a, b in pairs], [0, 1, 2, 3])
        bias = statistics.mean(b - a for a, b in pairs)   # + => more lenient than ref
        gross = sum(abs(a - b) >= 2 for a, b in pairs) / n
        cond = {}
        for t in (0, 1, 2, 3):
            ys = [b for a, b in pairs if a == t]
            cond[t] = statistics.mean(ys) if ys else None
        cstr = " ".join(f"{cond[t]:.1f}" if cond[t] is not None else " . " for t in (0, 1, 2, 3))
        # crude read: does it track? need rising conditional means + decent kappa
        vals = [cond[t] for t in (0, 1, 2, 3) if cond[t] is not None]
        tracks = len(vals) >= 3 and vals == sorted(vals) and (vals[-1] - vals[0]) >= 1.0
        if wk >= 0.4 and tracks:
            read = "careful"
        elif bias >= 0.8 and gross >= 0.35:
            read = "careless-lenient"
        elif wk < 0.1 and not tracks:
            read = "~random/misaligned"
        else:
            read = "mixed"
        print(f"{r:<6}{n:>5}{exact:>6.0%}{adj:>8.0%}{wk:>8.2f}"
              f"{bias:>+7.2f}{gross:>6.0%}      {cstr}        {read}")

    print("\nBaselines on a 0-3 scale: uniform-random -> exact~25%, wkappa~0, flat conditional means.")
    print("'bias' = rater_mean - reference_mean on shared items (+ = more lenient).")
    print("'gross' = share of shared items off by >=2 points.")


if __name__ == "__main__":
    main()
