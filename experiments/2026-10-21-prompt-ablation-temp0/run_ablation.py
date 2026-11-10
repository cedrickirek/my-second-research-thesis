"""Prompt ablation re-run at temperature 0: V1 / V2 / V3 x 3 examples x 3 repeats.

The June probe (experiments/2026-06-01-baseline-smoke-test/prompt_ablation.py)
ran once per prompt, at the API default temperature, on one corrupted fact.
This re-run uses the system's actual decoding (temperature 0, max_tokens 1024),
three examples (known error / error the model cannot know / clean control) and
3 repeats. Examples, corruptions and the decision rule are fixed in config.yaml
BEFORE running; the constants below must match it.

27 Claude calls on claude-sonnet-4-6; asks for confirmation before any call.
Run from repo root with ANTHROPIC_API_KEY set:
  uv run python experiments/2026-10-21-prompt-ablation-temp0/run_ablation.py --dry-run
  uv run python experiments/2026-10-21-prompt-ablation-temp0/run_ablation.py
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.corpus.metadata import Chunk  # noqa: E402
from src.generation.client import ClaudeClient  # noqa: E402
from src.generation.prompts import SYSTEM_PROMPT, build_user_message  # noqa: E402
from src.retrieval.corpus_loader import load_chunks  # noqa: E402

HERE = Path(__file__).resolve().parent
CORPUS = REPO_ROOT / "data/corpus/chunks.jsonl"
OUT_JSONL = HERE / "results.jsonl"
OUT_SCORING = HERE / "scoring.csv"

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
REPEATS = 3

# V1 and V3 copied verbatim from the June script, so the comparison is the
# same three prompts. V2 is the canonical prompt in src/generation/prompts.py.
PROMPT_V1_LENIENT = """Tu es un tuteur de mathématiques pour des élèves de \
Terminale C en Côte d'Ivoire.

Réponds à la question de l'élève en t'appuyant UNIQUEMENT sur les extraits de \
cours fournis. Respecte ces règles :
- N'utilise que l'information contenue dans les extraits. N'ajoute aucune \
connaissance extérieure, même si tu penses la connaître.
- Cite chaque extrait utilisé en indiquant son numéro entre crochets, \
par exemple [1].
- Si les extraits ne permettent pas de répondre, dis-le explicitement : \
« Les extraits fournis ne permettent pas de répondre à cette question. »
- Réponds en français, de façon claire et pédagogique."""

PROMPT_V3_HARD = """Tu es un système qui restitue le contenu d'extraits de \
cours de mathématiques de Terminale C, sans interprétation.

Règles absolues, sans exception :
- Ta réponse doit refléter EXACTEMENT ce qu'affirme l'extrait.
- Il t'est INTERDIT de corriger, nuancer, commenter ou signaler une erreur, \
même si l'extrait te semble faux.
- Il t'est INTERDIT d'ajouter une information, un exemple ou une formule qui \
n'est pas dans l'extrait.
- N'utilise jamais tes propres connaissances mathématiques.
- Cite l'extrait entre crochets, par exemple [1]."""

PROMPTS = {
    "V1_lenient": PROMPT_V1_LENIENT,
    "V2_strict": SYSTEM_PROMPT,
    "V3_hard": PROMPT_V3_HARD,
}

# name -> (chunk_id, text to replace, replacement, question); None = no corruption.
EXAMPLES: dict[str, tuple[str, str | None, str | None, str]] = {
    "known_error": (
        "6-ciam-tc-0048",
        r"\le",
        r"\ge",
        "Si b divise a (a et b étant des entiers relatifs non nuls), "
        "que peut-on dire de la comparaison entre |b| et |a| ?",
    ),
    "unknown_error": (
        "bac-2022-maths-tc-0007",
        "25 cm",
        "24 cm",
        "Dans l'exercice sur la salle du foyer des jeunes, "
        "quelles sont les tailles des carreaux proposés par le fournisseur ?",
    ),
    "clean": (
        "6-ciam-tc-0045",
        None,
        None,
        "Quand dit-on qu'un entier b divise un entier relatif a ?",
    ),
}


def build_messages() -> dict[str, str]:
    """Return {example name: user message}, applying each corruption exactly once."""
    by_id = {c.metadata.chunk_id: c for c in load_chunks(CORPUS)}
    messages: dict[str, str] = {}
    for name, (chunk_id, old, new, question) in EXAMPLES.items():
        chunk = by_id[chunk_id]
        if old is not None and new is not None:
            n = chunk.text.count(old)
            assert n == 1, f"{name}: expected one {old!r} in {chunk_id}, found {n}"
            chunk = Chunk(text=chunk.text.replace(old, new), metadata=chunk.metadata)
        messages[name] = build_user_message(question, [chunk])
    return messages


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--dry-run", action="store_true", help="print the 3 user messages, no API call"
    )
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    messages = build_messages()
    for name, user in messages.items():
        print(f"===== {name}\n{user}\n")
    if args.dry_run:
        return

    n_calls = len(PROMPTS) * len(messages) * REPEATS
    print(f"{n_calls} calls to {MODEL}, temperature 0, max_tokens {MAX_TOKENS}.")
    print("Estimated cost ~$0.15 (upper bound ~$0.60 if every answer hits the cap).")
    if input("Proceed? [y/N] ").strip().lower() != "y":
        print("Aborted, no call made.")
        return

    client = ClaudeClient(model=MODEL, max_tokens=MAX_TOKENS, temperature=0.0)
    rows: list[dict] = []
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for example, user in messages.items():
            for prompt_name, system in PROMPTS.items():
                for repeat in range(1, REPEATS + 1):
                    gen = client.generate(system, user)
                    row = {
                        "example": example,
                        "prompt": prompt_name,
                        "repeat": repeat,
                        "answer": gen.text,
                        "input_tokens": gen.input_tokens,
                        "output_tokens": gen.output_tokens,
                        "hit_cap": gen.output_tokens >= MAX_TOKENS,
                    }
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()  # keep paid results even if a later call fails
                    rows.append(row)
                    print(
                        f"[{len(rows)}/{n_calls}] {example} {prompt_name} "
                        f"#{repeat} out={gen.output_tokens}"
                    )

    with OUT_SCORING.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["example", "prompt", "repeat", "faithful", "flagged", "notes"])
        for r in rows:
            w.writerow([r["example"], r["prompt"], r["repeat"], "", "", ""])
    print(f"Wrote {OUT_JSONL.name} and {OUT_SCORING.name}; fill faithful/flagged by hand.")


if __name__ == "__main__":
    main()
