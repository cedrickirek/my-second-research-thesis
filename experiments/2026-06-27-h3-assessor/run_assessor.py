"""Run (or cost-estimate) the reframed-H3 LLM relevance-assessor over the 1,565 pairs.

Two modes:

  --estimate (default): OFFLINE cost/token estimate from the pair texts — makes NO
      API call. Use this to decide whether to run the paid batch.
  --run --confirm-cost: submits the paid Batch-API job (Claude Opus 4.8), polls to
      completion, and writes LLM labels in the SAME shape as the human labels so
      `analyze.py --labels <out>` consumes them unchanged. Each pair is scored
      n_runs (>=2) times under DISTINCT annotator ids (LLM_run1, LLM_run2, ...),
      so `analyze.py` reads cross-run self-consistency as the test-retest
      reliability and round-half-up-averages the runs into the LLM qrels.

The assessor's labels validate the assessor only (ranking + per-item agreement);
H1/H2 stay on the human qrels (circularity firewall, §M9.6).

Cost rule (CLAUDE.md): never call paid APIs in a loop without a cost estimate and a
confirmation. `--run` refuses to start unless `--confirm-cost` is also passed.

Estimate:
  uv run python experiments/2026-06-27-h3-assessor/run_assessor.py --estimate
Real run (after confirming the printed estimate):
  uv run python experiments/2026-06-27-h3-assessor/run_assessor.py --run --confirm-cost
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.eval.relevance.assessor import (  # noqa: E402
    RUBRIC_VERSION,
    RelevanceAssessor,
    build_user_prompt,
)

HERE = Path(__file__).resolve().parent
PAIRS = REPO_ROOT / "results/relevance_pairs.jsonl"
N_RUNS = 2  # >=2 for test-retest reliability (no temperature on Opus 4.8)

# Opus 4.8 pricing, USD per token (from the claude-api model table: $5 / $25 per MTok).
IN_PER_TOK = 5.0 / 1_000_000
OUT_PER_TOK = 25.0 / 1_000_000
CACHE_WRITE_MULT = 1.25  # 5-min ephemeral write
CACHE_READ_MULT = 0.10  # cached read
BATCH_MULT = 0.50  # Batch API is 50% of standard price
CHARS_PER_TOKEN = 3.5  # heuristic for FR + LaTeX (real run logs exact usage)
EST_OUTPUT_TOKENS = 70  # structured: one 0-3 grade + a one-sentence rationale
logger = logging.getLogger("h3_assessor")


def load_pairs(path: Path) -> list[dict]:
    pairs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        pairs.append(
            {
                "pair_id": r["pair_id"],
                "query_id": r["query_id"],
                "chunk_id": r["chunk_id"],
                "query_text": r.get("query_text", ""),
                "chunk_text": r.get("chunk_text", ""),
            }
        )
    return pairs


def _toks(text: str) -> float:
    return len(text) / CHARS_PER_TOKEN


def estimate(pairs: list[dict], assessor: RelevanceAssessor, n_runs: int) -> dict:
    """Offline token + cost estimate. No API call."""
    sys_tok = _toks(assessor.system_prompt)
    user_tok = sum(_toks(build_user_prompt(p["query_text"], p["chunk_text"])) for p in pairs)
    n_calls = len(pairs) * n_runs

    out_tok = EST_OUTPUT_TOKENS * n_calls
    user_tok_total = user_tok * n_runs

    # With prompt caching: system written once, read on every other call.
    sys_cost = sys_tok * IN_PER_TOK * (CACHE_WRITE_MULT + CACHE_READ_MULT * (n_calls - 1))
    user_cost = user_tok_total * IN_PER_TOK
    out_cost = out_tok * OUT_PER_TOK
    cached_batch = (sys_cost + user_cost + out_cost) * BATCH_MULT

    # No caching, no batch (worst case) — system re-billed in full every call.
    naive = (
        (sys_tok * n_calls + user_tok_total) * IN_PER_TOK + out_tok * OUT_PER_TOK
    )

    return {
        "n_pairs": len(pairs),
        "n_runs": n_runs,
        "n_calls": n_calls,
        "system_prompt_tokens": round(sys_tok),
        "mean_user_tokens": round(user_tok / len(pairs), 1),
        "total_input_tokens_uncached": round(user_tok_total),
        "est_output_tokens": out_tok,
        "model": assessor.model,
        "prompt_id": assessor.prompt_id,
        "cost_usd_cached_batch": round(cached_batch, 2),
        "cost_usd_naive_no_cache_no_batch": round(naive, 2),
        "note": (
            f"Heuristic at {CHARS_PER_TOKEN} chars/token (±~20%); the real run logs "
            "exact token usage. Caching assumes the rubric system prompt stays warm "
            "across the batch."
        ),
    }


def run_batch(
    pairs: list[dict], assessor: RelevanceAssessor, n_runs: int, out_suffix: str = ""
) -> None:
    """Submit the paid Batch-API job, poll, and write LLM labels + run metadata.

    `out_suffix` ("" for the full run, "_pilot" for a `--limit` pilot) keeps the
    pilot's outputs from clobbering the canonical full-batch files.
    """
    from anthropic import Anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    client = Anthropic()
    idx_to_meta: dict[str, dict] = {}
    requests = []
    for i, p in enumerate(pairs):
        params = assessor.request_params(p["query_text"], p["chunk_text"])
        for run in range(1, n_runs + 1):
            cid = f"p{i}r{run}"  # short, unique, charset-safe custom_id
            idx_to_meta[cid] = {**p, "run": run}
            requests.append(
                Request(custom_id=cid, params=MessageCreateParamsNonStreaming(**params))
            )

    logger.info("submitting batch: %d requests (%d pairs x %d runs)",
                len(requests), len(pairs), n_runs)
    batch = client.messages.batches.create(requests=requests)
    logger.info("batch id=%s status=%s", batch.id, batch.processing_status)

    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        logger.info("status=%s processing=%s", batch.processing_status,
                    batch.request_counts.processing)
        time.sleep(30)

    from src.eval.relevance.assessor import parse_response  # noqa: E402

    out_path = HERE / f"llm_labels{out_suffix}.jsonl"
    n_ok = n_err = in_tok = out_tok = 0
    with out_path.open("w", encoding="utf-8") as f:
        for result in client.messages.batches.results(batch.id):
            meta = idx_to_meta[result.custom_id]
            if result.result.type != "succeeded":
                n_err += 1
                logger.warning("custom_id=%s -> %s", result.custom_id, result.result.type)
                continue
            a = parse_response(result.result.message, assessor.model)
            in_tok += a.input_tokens
            out_tok += a.output_tokens
            n_ok += 1
            rec = {
                "pair_id": meta["pair_id"],
                "query_id": meta["query_id"],
                "chunk_id": meta["chunk_id"],
                "annotator_id": f"LLM_run{meta['run']}",
                "relevance": a.relevance,
                "notes": a.rationale,
                "model": a.model,
                "rubric_version": RUBRIC_VERSION,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    actual_cost = (in_tok * IN_PER_TOK + out_tok * OUT_PER_TOK) * BATCH_MULT
    meta = {
        "model": assessor.model,
        "prompt_id": assessor.prompt_id,
        "n_runs": n_runs,
        "n_succeeded": n_ok,
        "n_errored": n_err,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "approx_cost_usd_billed": round(actual_cost, 2),
        "labels": str(out_path.relative_to(REPO_ROOT)),
    }
    (HERE / f"run_meta{out_suffix}.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    (HERE / "assessor_prompt.txt").write_text(assessor.system_prompt, encoding="utf-8")
    logger.info("wrote %d labels -> %s (%d errored); ~$%.2f billed",
                n_ok, out_path, n_err, actual_cost)
    logger.info("next: uv run python experiments/2026-06-20-dispatch-analysis/analyze.py "
                "--labels %s  (LLM-qrels retrieval metrics + test-retest)", out_path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pairs", type=Path, default=PAIRS)
    ap.add_argument("--n-runs", type=int, default=N_RUNS)
    ap.add_argument("--estimate", action="store_true", help="offline cost estimate (default)")
    ap.add_argument("--run", action="store_true", help="submit the paid batch job")
    ap.add_argument("--confirm-cost", action="store_true",
                    help="required with --run; acknowledges the printed cost estimate")
    ap.add_argument("--limit", type=int, default=None,
                    help="pilot: only score the first N pairs (outputs go to *_pilot files)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    pairs = load_pairs(args.pairs)
    if args.limit is not None:
        pairs = pairs[: args.limit]
    suffix = "_pilot" if args.limit is not None else ""
    assessor = RelevanceAssessor()  # builds + locks the rubric prompt (no client yet)

    est = estimate(pairs, assessor, args.n_runs)
    label = "PILOT " if suffix else ""
    print(f"\n=== H3 assessor — {label}cost estimate (OFFLINE, no API call) ===")
    for k, v in est.items():
        print(f"  {k:32} {v}")
    (HERE / f"cost_estimate{suffix}.json").write_text(
        json.dumps(est, indent=2), encoding="utf-8"
    )

    if not args.run:
        print("\nEstimate only. To run the paid batch, re-invoke with: --run --confirm-cost")
        return
    if not args.confirm_cost:
        raise SystemExit("Refusing to run: pass --confirm-cost to acknowledge the cost estimate.")
    run_batch(pairs, assessor, args.n_runs, out_suffix=suffix)


if __name__ == "__main__":
    main()
