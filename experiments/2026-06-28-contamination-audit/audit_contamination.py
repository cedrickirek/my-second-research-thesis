"""Quantify worked-example contamination of the theory bucket (H2 limitation, §M5.5).

The pedagogical retriever (H2) enforces a theory+worked-example mix, but some chunks
tagged as theory-type are in fact *headingless worked examples* — a specific problem
solved step by step, lacking the "Exemple" heading the tagging heuristic keys on
(§M1 tagging, §M5.5). That contamination biases the H2 retrieval contrast
*conservatively*: the content-type-blind hybrid baseline can already surface
example-like content through its "theory" channel, partially closing the gap the
pedagogical retriever enforces by construction. §4.3/§5.3/m12 carry an [INSERT] for
the contamination rate; this script measures it.

Method: an LLM classifier (Claude Opus 4.8, the same judge family as the H3 assessor)
labels every theory-bucket chunk as either genuine expository THEORY (definition,
theorem statement, property, method exposition, proof) or a headingless WORKED EXAMPLE
(a specific numeric/algebraic instance being solved step by step). Each chunk is
classified n_runs (>=2) times for a test-retest reliability read, exactly as the H3
assessor does (Opus 4.8 has no temperature; §M9.2). The contamination rate is the
share of theory-bucket chunks whose majority label is WORKED EXAMPLE, with a Wilson
95% CI.

Theory bucket = content_type in {theory, theorem, definition, remark, proof} (the
§M5.2 bucket aggregate; 514 chunks). Example/solution/exercise chunks are NOT audited
— they are already correctly typed.

Cost rule (CLAUDE.md): never call a paid API in a loop without a cost estimate and a
confirmation. `--run` refuses to start unless `--confirm-cost` is also passed.

Estimate (offline, no API call):
  uv run python experiments/2026-06-28-contamination-audit/audit_contamination.py --estimate
Real run (after confirming the printed estimate):
  uv run python experiments/2026-06-28-contamination-audit/audit_contamination.py --run --confirm-cost
Score (free, after the run):
  uv run python experiments/2026-06-28-contamination-audit/audit_contamination.py --score
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

HERE = Path(__file__).resolve().parent
CORPUS = REPO_ROOT / "data/corpus/chunks.jsonl"
LABELS = HERE / "labels.jsonl"

MODEL = "claude-opus-4-8"  # same judge family as the H3 assessor; no temperature
MAX_TOKENS = 512
N_RUNS = 2  # >=2 for test-retest reliability (Opus 4.8 has no temperature; §M9.2)
THEORY_BUCKET = {"theory", "theorem", "definition", "remark", "proof"}

# Opus 4.8 pricing, USD/token (claude-api model table: $5 / $25 per MTok), Batch -50%.
IN_PER_TOK = 5.0 / 1_000_000
OUT_PER_TOK = 25.0 / 1_000_000
CACHE_WRITE_MULT = 1.25
CACHE_READ_MULT = 0.10
BATCH_MULT = 0.50
CHARS_PER_TOKEN = 3.5  # FR + LaTeX heuristic; the real run logs exact usage
EST_OUTPUT_TOKENS = 60

logger = logging.getLogger("contamination_audit")

LABEL_FORMAT = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": ["THEORY", "WORKED_EXAMPLE"]},
            "rationale": {"type": "string"},
        },
        "required": ["label", "rationale"],
        "additionalProperties": False,
    },
}

SYSTEM_PROMPT = (
    "Tu es enseignant(e) de mathématiques de Terminale C (Côte d'Ivoire). On te donne "
    "un passage d'un manuel de cours qui a été automatiquement étiqueté comme « théorie ». "
    "Ta tâche : déterminer si ce passage est RÉELLEMENT de la théorie, ou s'il s'agit en "
    "fait d'un EXEMPLE RÉSOLU sans titre « Exemple ».\n\n"
    "Définitions :\n"
    "- THEORY : exposé général — une définition, l'énoncé d'un théorème ou d'une propriété, "
    "une méthode décrite en général, une démonstration. Le passage énonce ou explique un "
    "résultat, sans résoudre un cas particulier précis.\n"
    "- WORKED_EXAMPLE : un cas particulier concret traité étape par étape — on calcule, on "
    "résout, on applique une méthode à des valeurs/expressions précises (« Calculons… », "
    "« On a… donc… », résolution d'une équation donnée, étude d'une fonction donnée), même "
    "si le mot « Exemple » est absent.\n\n"
    "Le critère décisif : un EXEMPLE RÉSOLU traite UN cas précis du début à la fin ; la "
    "THÉORIE énonce le résultat général sans le dérouler sur un cas particulier. En cas de "
    "doute entre une démonstration générale (THEORY) et un exemple résolu (WORKED_EXAMPLE), "
    "demande-toi si un élève y verrait « comment on fait sur un cas » (WORKED_EXAMPLE) ou "
    "« ce qu'il faut savoir » (THEORY).\n\n"
    "Réponds par UNE étiquette (THEORY ou WORKED_EXAMPLE) et une justification d'une phrase."
)


def prompt_id() -> str:
    import hashlib

    return hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:16]


def load_theory_bucket(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        if c["metadata"]["content_type"] in THEORY_BUCKET:
            out.append(
                {
                    "chunk_id": c["metadata"]["chunk_id"],
                    "content_type": c["metadata"]["content_type"],
                    "text": c["text"],
                }
            )
    return out


def user_prompt(chunk_text: str) -> str:
    return (
        f"PASSAGE ÉTIQUETÉ « théorie » :\n{chunk_text}\n\n"
        "Ce passage est-il réellement de la THEORY, ou un WORKED_EXAMPLE sans titre ?"
    )


def request_params(chunk_text: str) -> dict:
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
        ],
        "messages": [{"role": "user", "content": user_prompt(chunk_text)}],
        "output_config": {"format": LABEL_FORMAT},
    }


def _toks(text: str) -> float:
    return len(text) / CHARS_PER_TOKEN


def estimate(chunks: list[dict], n_runs: int) -> dict:
    sys_tok = _toks(SYSTEM_PROMPT)
    user_tok = sum(_toks(user_prompt(c["text"])) for c in chunks)
    n_calls = len(chunks) * n_runs
    out_tok = EST_OUTPUT_TOKENS * n_calls
    user_tok_total = user_tok * n_runs
    sys_cost = sys_tok * IN_PER_TOK * (CACHE_WRITE_MULT + CACHE_READ_MULT * (n_calls - 1))
    user_cost = user_tok_total * IN_PER_TOK
    out_cost = out_tok * OUT_PER_TOK
    cached_batch = (sys_cost + user_cost + out_cost) * BATCH_MULT
    naive = (sys_tok * n_calls + user_tok_total) * IN_PER_TOK + out_tok * OUT_PER_TOK
    return {
        "n_chunks": len(chunks),
        "n_runs": n_runs,
        "n_calls": n_calls,
        "model": MODEL,
        "prompt_id": prompt_id(),
        "system_prompt_tokens": round(sys_tok),
        "cost_usd_cached_batch": round(cached_batch, 2),
        "cost_usd_naive_no_cache_no_batch": round(naive, 2),
        "note": f"Heuristic at {CHARS_PER_TOKEN} chars/token (±~20%); the run logs exact usage.",
    }


def run_batch(chunks: list[dict], n_runs: int) -> None:
    from anthropic import Anthropic
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    client = Anthropic()
    cid_to_meta: dict[str, dict] = {}
    requests = []
    for i, c in enumerate(chunks):
        params = request_params(c["text"])
        for run in range(1, n_runs + 1):
            cid = f"c{i}r{run}"
            cid_to_meta[cid] = {**c, "run": run}
            requests.append(
                Request(custom_id=cid, params=MessageCreateParamsNonStreaming(**params))
            )

    logger.info("submitting batch: %d requests (%d chunks x %d runs)",
                len(requests), len(chunks), n_runs)
    batch = client.messages.batches.create(requests=requests)
    logger.info("batch id=%s status=%s", batch.id, batch.processing_status)
    while True:
        batch = client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        logger.info("status=%s processing=%s", batch.processing_status,
                    batch.request_counts.processing)
        time.sleep(30)

    n_ok = n_err = in_tok = out_tok = 0
    with LABELS.open("w", encoding="utf-8") as f:
        for result in client.messages.batches.results(batch.id):
            meta = cid_to_meta[result.custom_id]
            if result.result.type != "succeeded":
                n_err += 1
                logger.warning("custom_id=%s -> %s", result.custom_id, result.result.type)
                continue
            resp = result.result.message
            text = "".join(b.text for b in resp.content if b.type == "text")
            data = json.loads(text)
            u = resp.usage
            in_tok += getattr(u, "input_tokens", 0)
            out_tok += getattr(u, "output_tokens", 0)
            n_ok += 1
            f.write(json.dumps({
                "chunk_id": meta["chunk_id"],
                "content_type": meta["content_type"],
                "run": meta["run"],
                "label": data["label"],
                "rationale": data.get("rationale", ""),
                "model": MODEL,
            }, ensure_ascii=False) + "\n")

    cost = (in_tok * IN_PER_TOK + out_tok * OUT_PER_TOK) * BATCH_MULT
    (HERE / "run_meta.json").write_text(json.dumps({
        "model": MODEL, "prompt_id": prompt_id(), "n_runs": n_runs,
        "n_succeeded": n_ok, "n_errored": n_err,
        "input_tokens": in_tok, "output_tokens": out_tok,
        "approx_cost_usd_billed": round(cost, 2),
    }, indent=2), encoding="utf-8")
    (HERE / "classifier_prompt.txt").write_text(SYSTEM_PROMPT, encoding="utf-8")
    logger.info("wrote %d labels -> %s (%d errored); ~$%.2f billed", n_ok, LABELS, n_err, cost)
    score()


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% CI for a binomial proportion (better than normal approx for rates near 0)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def score() -> None:
    if not LABELS.exists():
        raise SystemExit(f"no labels at {LABELS} — run with --run --confirm-cost first")
    by_chunk: dict[str, dict[int, str]] = defaultdict(dict)
    ctype: dict[str, str] = {}
    for line in LABELS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        by_chunk[r["chunk_id"]][r["run"]] = r["label"]
        ctype[r["chunk_id"]] = r["content_type"]

    # Majority label per chunk (ties -> WORKED_EXAMPLE, the conservative call: counts
    # a borderline chunk as contamination, so the reported rate is an upper-ish bound).
    n = len(by_chunk)
    we_chunks = []
    agree = 0
    for cid, runs in by_chunk.items():
        labels = list(runs.values())
        cnt = Counter(labels)
        if len(set(labels)) == 1:
            agree += 1
        majority = "WORKED_EXAMPLE" if cnt["WORKED_EXAMPLE"] >= cnt["THEORY"] else "THEORY"
        if majority == "WORKED_EXAMPLE":
            we_chunks.append(cid)

    k = len(we_chunks)
    rate = k / n if n else 0.0
    lo, hi = _wilson(k, n)

    # contamination by source content_type (where it concentrates)
    by_type = Counter(ctype[c] for c in we_chunks)
    type_totals = Counter(ctype.values())

    report = {
        "n_theory_bucket_chunks": n,
        "n_runs": max((len(r) for r in by_chunk.values()), default=0),
        "test_retest_agreement": round(agree / n, 4) if n else 0.0,
        "n_worked_example": k,
        "contamination_rate": round(rate, 4),
        "contamination_rate_pct": round(rate * 100, 1),
        "wilson_95ci_pct": [round(lo * 100, 1), round(hi * 100, 1)],
        "by_source_content_type": {
            t: {"contaminated": by_type.get(t, 0), "total": type_totals[t],
                "pct": round(100 * by_type.get(t, 0) / type_totals[t], 1)}
            for t in sorted(type_totals)
        },
    }
    (HERE / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    print("\n=== Theory-bucket contamination (worked examples mistagged as theory) ===")
    print(f"  chunks audited: {n}  (n_runs={report['n_runs']}, "
          f"test-retest agreement {report['test_retest_agreement']:.1%})")
    print(f"  worked examples: {k}/{n} = {report['contamination_rate_pct']}%  "
          f"(Wilson 95% CI {report['wilson_95ci_pct'][0]}–{report['wilson_95ci_pct'][1]}%)")
    print("  by source content_type:")
    for t, d in report["by_source_content_type"].items():
        print(f"    {t:12} {d['contaminated']:>3}/{d['total']:<3} ({d['pct']}%)")
    print(f"\nreport -> {HERE / 'report.json'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--n-runs", type=int, default=N_RUNS)
    ap.add_argument("--estimate", action="store_true", help="offline cost estimate (default)")
    ap.add_argument("--run", action="store_true", help="submit the paid batch job")
    ap.add_argument("--confirm-cost", action="store_true",
                    help="required with --run; acknowledges the printed cost estimate")
    ap.add_argument("--score", action="store_true", help="score existing labels (free)")
    ap.add_argument("--limit", type=int, default=None, help="pilot: only the first N chunks")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if args.score:
        score()
        return

    chunks = load_theory_bucket(args.corpus)
    if args.limit is not None:
        chunks = chunks[: args.limit]

    est = estimate(chunks, args.n_runs)
    print("\n=== Contamination audit — cost estimate (OFFLINE, no API call) ===")
    for k, v in est.items():
        print(f"  {k:34} {v}")
    (HERE / "cost_estimate.json").write_text(json.dumps(est, indent=2), encoding="utf-8")

    if not args.run:
        print("\nEstimate only. To run the paid batch: --run --confirm-cost")
        return
    if not args.confirm_cost:
        raise SystemExit("Refusing to run: pass --confirm-cost to acknowledge the cost.")
    run_batch(chunks, args.n_runs)


if __name__ == "__main__":
    main()
