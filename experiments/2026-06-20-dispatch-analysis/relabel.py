"""Relabel a returned annotation file under a new annotator code.

When an extra teacher graded a file that was internally baked as someone else
(e.g. used a file coded T08 but should count as T11), their export still carries
the OLD `annotator_id` — renaming the file does NOT change the id inside, and the
analyzer reads `annotator_id` from the records. This rewrites it and writes a
clean copy to `<folder>/clean/<NEWCODE>.jsonl`, never modifying the input.

  uv run python experiments/2026-06-20-dispatch-analysis/relabel.py \
      experiments/annotated/T11_old-T08_2026-05-29.jsonl --to T11

Run it for EVERY return (including the already-correct originals, e.g. `--to T03`
on the T03 file) so `clean/` holds the full, correctly-coded set; then point
`analyze.py --labels "experiments/annotated/clean/*.jsonl"`.

Refuses if the file mixes annotators (not a single clean return) unless --force.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input", type=Path)
    ap.add_argument("--to", required=True, help="new annotator code, e.g. T11")
    ap.add_argument("--out", type=Path, default=None, help="output path (default: <folder>/clean/<TO>.jsonl)")
    ap.add_argument("--force", action="store_true", help="proceed even if the file has multiple annotators")
    args = ap.parse_args()

    recs = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not recs:
        raise SystemExit(f"{args.input} is empty")
    ids = Counter(r.get("annotator_id") for r in recs)
    if len(ids) != 1 and not args.force:
        raise SystemExit(
            f"{args.input.name} has multiple annotator_ids {dict(ids)} — not a single "
            "return. Re-check the file, or pass --force."
        )
    src = ids.most_common(1)[0][0]
    graded = sum(1 for r in recs if r.get("relevance") is not None)
    for r in recs:
        r["annotator_id"] = args.to

    out = args.out or (args.input.parent / "clean" / f"{args.to}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise SystemExit(f"{out} already exists — code {args.to} used twice? choose another --to or --out.")
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")
    print(f"{args.input.name}: {len(recs)} records, {graded} graded | annotator {src} -> {args.to}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()