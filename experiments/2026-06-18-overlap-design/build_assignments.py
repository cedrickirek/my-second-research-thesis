"""Build the teacher-annotation overlap design (task #14) for the #12 pairs.

Deterministic (seed 42). Produces three assignment maps from
`data/eval/queries.jsonl` + `results/relevance_pairs.jsonl`:

  * pilot  — 2 teachers, a small stratified set, BOTH grade everything
             (task #15: shake out the app + rubric, revise v0.1 -> v1.0).
  * disp10 — dispatch with 10 teachers (recommended): anchor 10 queries x2
             raters + 90 coverage queries x1 rater => ~11 queries/teacher.
             Sized to keep each teacher's load light (~173 pairs) while still
             covering all 100 queries and measuring agreement.
  * disp05 — contingency with 5 teachers: anchor 10 queries x3 raters + 90
             coverage x1 (if only ~5 of the over-recruited 10 materialise).

Assignment is BY QUERY: a query's ~15.7 pairs always stay with the same
grader, so context is not fragmented. The anchor is stratified-random by
bucket (matches the 60/20/20 split) and spread across chapters, so the agreement
estimate (Krippendorff's alpha) represents the whole task, not a hard subset.

Outputs one JSON per design + a printed summary. Query-level is canonical; the
app expands each assigned query into its pairs at seed time.

Run from repo root::

    uv run python "experiments/2026-06-18-overlap-design/build_assignments.py"
"""

from __future__ import annotations

import collections
import json
import random
from pathlib import Path

SEED = 42
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
QUERIES = REPO_ROOT / "data" / "eval" / "queries.jsonl"
PAIRS = REPO_ROOT / "results" / "relevance_pairs.jsonl"

N_ANCHOR = 10


def load_queries() -> list[dict]:
    out = []
    for line in QUERIES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        q = json.loads(line)
        lecons = q.get("lecons") or ["unknown"]
        out.append(
            {
                "query_id": q["query_id"],
                "bucket": q.get("bucket", "unknown"),
                "chapter": lecons[0],
                "question_type": q.get("question_type", "unknown"),
            }
        )
    return out


def pairs_per_query() -> dict[str, int]:
    counts: collections.Counter[str] = collections.Counter()
    for line in PAIRS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            counts[json.loads(line)["query_id"]] += 1
    return counts


def stratified_anchor(queries: list[dict], n: int, seed: int) -> list[str]:
    """Pick n anchor query_ids: proportional by bucket, spread across chapters."""
    rng = random.Random(seed)
    by_bucket: dict[str, list[dict]] = collections.defaultdict(list)
    for q in queries:
        by_bucket[q["bucket"]].append(q)

    total = len(queries)
    # Largest-remainder allocation so the per-bucket targets sum to exactly n.
    raw = {b: n * len(qs) / total for b, qs in by_bucket.items()}
    targets = {b: int(v) for b, v in raw.items()}
    while sum(targets.values()) < n:
        b = max(raw, key=lambda b: raw[b] - targets[b])
        targets[b] += 1

    anchor: list[str] = []
    for bucket, qs in by_bucket.items():
        need = targets[bucket]
        # Round-robin across chapters for breadth: one query per chapter per pass.
        by_chap: dict[str, list[dict]] = collections.defaultdict(list)
        for q in qs:
            by_chap[q["chapter"]].append(q)
        for chap in by_chap:
            rng.shuffle(by_chap[chap])
        chapters = sorted(by_chap)
        rng.shuffle(chapters)
        picked: list[str] = []
        while len(picked) < need:
            progressed = False
            for chap in chapters:
                if by_chap[chap]:
                    picked.append(by_chap[chap].pop()["query_id"])
                    progressed = True
                    if len(picked) == need:
                        break
            if not progressed:
                break
        anchor.extend(picked)
    return sorted(anchor)


def allocate_coverage(
    coverage: list[str], teachers: list[str], pcount: dict[str, int]
) -> dict[str, list[str]]:
    """Greedy: give each query to the teacher with the lightest pair load."""
    load = {t: 0 for t in teachers}
    out: dict[str, list[str]] = {t: [] for t in teachers}
    for qid in sorted(coverage, key=lambda q: (-pcount[q], q)):
        t = min(teachers, key=lambda t: (load[t], t))
        out[t].append(qid)
        load[t] += pcount[qid]
    return out


def allocate_anchor_raters(
    anchor: list[str], teachers: list[str], raters: int
) -> dict[str, list[str]]:
    """Sliding window of `raters` over teachers: balanced load, varied pairings."""
    n = len(teachers)
    out: dict[str, list[str]] = {t: [] for t in teachers}
    for i, qid in enumerate(sorted(anchor)):
        for j in range(raters):
            out[teachers[(i + j) % n]].append(qid)
    return out


def build(
    name: str, teachers: list[str], anchor: list[str], raters: int, pcount: dict[str, int]
) -> dict:
    anchor_set = set(anchor)
    coverage = [qid for qid in pcount if qid not in anchor_set]
    cov = allocate_coverage(coverage, teachers, pcount)
    anc = allocate_anchor_raters(anchor, teachers, raters)

    per_teacher = {}
    for t in teachers:
        aq, cq = sorted(anc[t]), sorted(cov[t])
        n_pairs = sum(pcount[q] for q in aq) + sum(pcount[q] for q in cq)
        per_teacher[t] = {
            "anchor_queries": aq,
            "coverage_queries": cq,
            "n_queries": len(aq) + len(cq),
            "n_pairs": n_pairs,
        }
    total_judgments = sum(v["n_pairs"] for v in per_teacher.values())
    return {
        "design": name,
        "seed": SEED,
        "n_teachers": len(teachers),
        "anchor_raters": raters,
        "n_anchor_queries": len(anchor),
        "n_coverage_queries": len(coverage),
        "anchor_query_ids": sorted(anchor),
        "per_teacher": per_teacher,
        "totals": {
            "distinct_pairs": sum(pcount.values()),
            "total_human_judgments": total_judgments,
            "min_pairs_per_teacher": min(v["n_pairs"] for v in per_teacher.values()),
            "max_pairs_per_teacher": max(v["n_pairs"] for v in per_teacher.values()),
        },
    }


def build_pilot(queries: list[dict], pcount: dict[str, int]) -> dict:
    """2 teachers, 5 stratified queries, BOTH grade all (redundancy 2)."""
    rng = random.Random(SEED + 1)
    by_bucket: dict[str, list[dict]] = collections.defaultdict(list)
    for q in queries:
        by_bucket[q["bucket"]].append(q)
    plan = {"single_lecon": 3, "multi_notion": 1, "hard_edge": 1}
    picked: list[str] = []
    for bucket, k in plan.items():
        pool = list(by_bucket.get(bucket, []))
        rng.shuffle(pool)
        picked.extend(q["query_id"] for q in pool[:k])
    picked = sorted(picked)
    teachers = ["T01", "T02"]
    n_pairs = sum(pcount[q] for q in picked)
    return {
        "design": "pilot",
        "seed": SEED + 1,
        "n_teachers": 2,
        "note": "BOTH teachers grade ALL pilot queries (redundancy 2). Purpose: "
        "test app + rubric, measure preliminary agreement, lock rubric v0.1 -> "
        "v1.0. Pilot labels are graded under v0.1 and are for process calibration, "
        "NOT final gold; re-grade under v1.0 at dispatch.",
        "pilot_query_ids": picked,
        "per_teacher": {t: {"queries": picked, "n_pairs": n_pairs} for t in teachers},
        "totals": {"distinct_pairs": n_pairs, "total_human_judgments": n_pairs * 2},
    }


def summarize(d: dict) -> None:
    print(f"\n=== {d['design']} ===")
    if d["design"] == "pilot":
        print(f"  2 teachers x {len(d['pilot_query_ids'])} queries "
              f"({d['totals']['distinct_pairs']} pairs) graded by both "
              f"-> {d['totals']['total_human_judgments']} judgments")
        print(f"  queries: {', '.join(d['pilot_query_ids'])}")
        return
    print(f"  {d['n_teachers']} teachers | anchor {d['n_anchor_queries']} queries "
          f"x{d['anchor_raters']} raters | coverage {d['n_coverage_queries']} x1")
    print(f"  total human judgments: {d['totals']['total_human_judgments']} | "
          f"per-teacher pairs: {d['totals']['min_pairs_per_teacher']}–"
          f"{d['totals']['max_pairs_per_teacher']}")
    for t, v in d["per_teacher"].items():
        print(f"    {t}: {v['n_queries']:2d} queries ({len(v['anchor_queries'])} anchor "
              f"+ {len(v['coverage_queries'])} coverage) = {v['n_pairs']} pairs")


def main() -> None:
    queries = load_queries()
    pcount = pairs_per_query()
    assert len(queries) == len(pcount), "every query must have pairs"

    bucket_dist = collections.Counter(q["bucket"] for q in queries)
    print(f"loaded {len(queries)} queries, {sum(pcount.values())} pairs")
    print(f"bucket distribution: {dict(bucket_dist)}")

    anchor = stratified_anchor(queries, N_ANCHOR, SEED)
    anchor_buckets = collections.Counter(
        q["bucket"] for q in queries if q["query_id"] in set(anchor)
    )
    anchor_chaps = collections.Counter(
        q["chapter"] for q in queries if q["query_id"] in set(anchor)
    )
    print(f"anchor: {len(anchor)} queries | buckets {dict(anchor_buckets)} | "
          f"{len(anchor_chaps)} chapters covered")

    designs = {
        "pilot": build_pilot(queries, pcount),
        "disp10": build("disp10", [f"T{i:02d}" for i in range(1, 11)], anchor, 2, pcount),
        "disp05": build("disp05", [f"T{i:02d}" for i in range(1, 6)], anchor, 3, pcount),
    }
    for name, d in designs.items():
        (HERE / f"assignments_{name}.json").write_text(
            json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summarize(d)
    print(f"\nwrote {len(designs)} assignment files to {HERE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
