"""Fetch results for an ALREADY-SUBMITTED H3 assessor batch and write the labels.

Safety net: if the poller in run_assessor.py died (e.g. laptop slept/shut down) before
the batch ended, run this once the batch shows 'ended' to download + write the labels
in the same shape run_assessor.py would have. Reconstructs the custom_id -> pair map
from results/relevance_pairs.jsonl in the same order the run used.

  uv run python experiments/2026-06-27-h3-assessor/fetch_batch.py [BATCH_ID]
  (BATCH_ID defaults to the full v1.1 batch submitted 2026-06-27.)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.assessor import (  # noqa: E402
    MODEL,
    RUBRIC_VERSION,
    parse_response,
)

HERE = Path(__file__).resolve().parent
PAIRS = REPO_ROOT / "results/relevance_pairs.jsonl"
N_RUNS = 2
DEFAULT_BATCH_ID = "msgbatch_01NLRqBZXfanxaBV2iwzZRTw"

# Opus 4.8 pricing (Batch API = 50%); matches run_assessor.py.
IN_PER_TOK, OUT_PER_TOK, BATCH_MULT = 5.0 / 1_000_000, 25.0 / 1_000_000, 0.50


def load_pairs(path: Path) -> list[dict]:
    pairs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            pairs.append(
                {"pair_id": r["pair_id"], "query_id": r["query_id"], "chunk_id": r["chunk_id"]}
            )
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("batch_id", nargs="?", default=DEFAULT_BATCH_ID)
    ap.add_argument("--n-runs", type=int, default=N_RUNS)
    ap.add_argument("--suffix", default="", help="output suffix (use _pilot for a pilot batch)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    from anthropic import Anthropic

    client = Anthropic()
    batch = client.messages.batches.retrieve(args.batch_id)
    print(f"status: {batch.processing_status}  counts: {batch.request_counts}")
    if batch.processing_status != "ended":
        print("Not ended yet — re-run this when the status is 'ended'.")
        return

    pairs = load_pairs(PAIRS)
    idx_to_meta: dict[str, dict] = {}
    for i, p in enumerate(pairs):
        for run in range(1, args.n_runs + 1):
            idx_to_meta[f"p{i}r{run}"] = {**p, "run": run}

    out_path = HERE / f"llm_labels{args.suffix}.jsonl"
    n_ok = n_err = in_tok = out_tok = 0
    with out_path.open("w", encoding="utf-8") as f:
        for result in client.messages.batches.results(args.batch_id):
            meta = idx_to_meta[result.custom_id]
            if result.result.type != "succeeded":
                n_err += 1
                continue
            a = parse_response(result.result.message, MODEL)
            in_tok += a.input_tokens
            out_tok += a.output_tokens
            n_ok += 1
            f.write(
                json.dumps(
                    {
                        "pair_id": meta["pair_id"],
                        "query_id": meta["query_id"],
                        "chunk_id": meta["chunk_id"],
                        "annotator_id": f"LLM_run{meta['run']}",
                        "relevance": a.relevance,
                        "notes": a.rationale,
                        "model": a.model,
                        "rubric_version": RUBRIC_VERSION,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    cost = (in_tok * IN_PER_TOK + out_tok * OUT_PER_TOK) * BATCH_MULT
    (HERE / f"run_meta{args.suffix}.json").write_text(
        json.dumps(
            {
                "model": MODEL,
                "rubric_version": RUBRIC_VERSION,
                "n_runs": args.n_runs,
                "n_succeeded": n_ok,
                "n_errored": n_err,
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "approx_cost_usd_billed": round(cost, 2),
                "labels": str(out_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {n_ok} labels -> {out_path} ({n_err} errored); ~${cost:.2f} billed")


if __name__ == "__main__":
    main()
