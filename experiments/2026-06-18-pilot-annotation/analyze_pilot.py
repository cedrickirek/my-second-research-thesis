"""Analyze the returned 2-teacher pilot labels (#15).

Reads the two exported files (pilot_T01_*.jsonl, pilot_T02_*.jsonl) from this
folder, joins on pair_id, and reports:

  * coverage (how many of the 80 pairs each teacher graded),
  * agreement: exact, adjacent (|diff|<=1), binary relevant (score>=2),
    Cohen's kappa on the binary, and quadratic-weighted Cohen's kappa on 0-3,
  * a DISAGREEMENT list (|diff|>=1) with the query + chunk + both notes — the
    actionable output: each disagreement is a candidate rubric ambiguity to
    resolve before locking v1.0.

No third-party deps (kappa implemented inline). This is a 2-rater pilot read,
not the H3 result — that uses Krippendorff's alpha over the full anchor.

Run from repo root (after dropping the two returned files here)::

    uv run python "experiments/2026-06-18-pilot-annotation/analyze_pilot.py"
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
PAIRS = REPO_ROOT / "results" / "relevance_pairs.jsonl"


def load_labels(annotator_glob: str) -> dict[str, dict]:
    files = sorted(HERE.glob(annotator_glob))
    if not files:
        return {}
    rows = {}
    for line in files[-1].read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["pair_id"]] = r
    return rows


def cohen_kappa(pairs: list[tuple[int, int]], categories: list[int]) -> float:
    """Unweighted Cohen's kappa for two raters over discrete categories."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    obs = [[0] * k for _ in range(k)]
    for a, b in pairs:
        obs[idx[a]][idx[b]] += 1
    po = sum(obs[i][i] for i in range(k)) / n
    r = [sum(obs[i]) / n for i in range(k)]
    c = [sum(obs[i][j] for i in range(k)) / n for j in range(k)]
    pe = sum(r[i] * c[i] for i in range(k))
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def weighted_kappa(pairs: list[tuple[int, int]]) -> float:
    """Quadratic-weighted Cohen's kappa over the 0-3 ordinal scale."""
    cats = [0, 1, 2, 3]
    n = len(pairs)
    if n == 0:
        return float("nan")
    w = [[((i - j) ** 2) / 9 for j in cats] for i in cats]
    obs = [[0.0] * 4 for _ in range(4)]
    for a, b in pairs:
        obs[a][b] += 1
    row = [sum(obs[i]) for i in range(4)]
    col = [sum(obs[i][j] for i in range(4)) for j in range(4)]
    num = sum(w[i][j] * obs[i][j] for i in cats for j in cats)
    den = sum(w[i][j] * row[i] * col[j] / n for i in cats for j in cats)
    return 1.0 if den == 0 else 1 - num / den


def main() -> None:
    t1 = load_labels("pilot_T01_*.jsonl")
    t2 = load_labels("pilot_T02_*.jsonl")
    if not t1 or not t2:
        print("Waiting on returned files. Drop pilot_T01_*.jsonl and "
              "pilot_T02_*.jsonl into this folder, then re-run.")
        print(f"  found T01: {len(t1)} rows | T02: {len(t2)} rows")
        return

    chunk_by_pair = {}
    for line in PAIRS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            p = json.loads(line)
            chunk_by_pair[p["pair_id"]] = p

    both = [pid for pid in t1 if pid in t2
            and t1[pid].get("relevance") is not None
            and t2[pid].get("relevance") is not None]
    print(f"graded by T01: {sum(v.get('relevance') is not None for v in t1.values())}/{len(t1)}")
    print(f"graded by T02: {sum(v.get('relevance') is not None for v in t2.values())}/{len(t2)}")
    print(f"pairs graded by BOTH: {len(both)}\n")

    pairs = [(t1[p]["relevance"], t2[p]["relevance"]) for p in both]
    exact = sum(a == b for a, b in pairs) / len(pairs)
    adjacent = sum(abs(a - b) <= 1 for a, b in pairs) / len(pairs)
    binp = [(int(a >= 2), int(b >= 2)) for a, b in pairs]
    binary = sum(a == b for a, b in binp) / len(binp)

    print("=== Agreement (2 raters, pilot) ===")
    print(f"  exact (same 0-3):        {exact:5.1%}")
    print(f"  adjacent (|diff|<=1):    {adjacent:5.1%}")
    print(f"  binary relevant (>=2):   {binary:5.1%}")
    print(f"  Cohen kappa (binary):    {cohen_kappa(binp, [0,1]):.3f}")
    print(f"  weighted kappa (0-3):    {weighted_kappa(pairs):.3f}")
    dist = collections.Counter(abs(a - b) for a, b in pairs)
    print(f"  |diff| distribution:     {dict(sorted(dist.items()))}\n")

    disagree = sorted(
        (p for p in both if abs(t1[p]["relevance"] - t2[p]["relevance"]) >= 1),
        key=lambda p: -abs(t1[p]["relevance"] - t2[p]["relevance"]),
    )
    print(f"=== Disagreements ({len(disagree)}) — candidate rubric ambiguities ===")
    for pid in disagree:
        c = chunk_by_pair.get(pid, {})
        print(f"\n[{t1[pid]['relevance']} vs {t2[pid]['relevance']}] {pid}")
        print(f"  Q: {(c.get('query_text') or '')[:100]}")
        print(f"  chunk: [{c.get('chunk_content_type')}] {(c.get('chunk_heading') or '')[:70]}")
        for who, t in (("T01", t1), ("T02", t2)):
            note = (t[pid].get("notes") or "").strip()
            if note:
                print(f"  {who} note: {note[:120]}")


if __name__ == "__main__":
    main()