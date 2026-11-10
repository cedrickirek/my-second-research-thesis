"""Prompt ablation for the grounding-injection test.

Re-runs ONE controlled test under three system prompts to see whether stronger
instructions stop the model from overriding a (deliberately false) extract.

Context is a single poisoned extract: CIAM chunk 0005 with its inequality
flipped from |b| <= |a| to the FALSE |b| >= |a|. The question asks what holds
for |b| vs |a|. For each prompt we observe whether the model:
  - reports the false |b| >= |a|  (faithful to source), or
  - answers the true  |b| <= |a|  (overrides with its own knowledge).

No retrieval/embedding model needed (context is fixed). Makes 3 Claude calls
(a fraction of a cent). Run from repo root with ANTHROPIC_API_KEY set:
  uv run python experiments/2026-06-01-baseline-smoke-test/prompt_ablation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.corpus.metadata import Chunk  # noqa: E402
from src.generation.client import ClaudeClient  # noqa: E402
from src.generation.prompts import build_user_message  # noqa: E402
from src.retrieval.corpus_loader import load_chunks  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
SUBSET = SCRIPT_DIR / "smoke_chunks.jsonl"
OUT = SCRIPT_DIR / "prompt_ablation.json"

POISON_CHUNK_ID = "extract-ciam-tc-0005"
GROUNDING_QUESTION = (
    "Si b divise a (a et b étant des entiers relatifs non nuls), "
    "que peut-on dire de la comparaison entre |b| et |a| ?"
)

# V1: the original lenient prompt (canonical before the ablation promoted V2).
# Pinned here as a literal so this experiment keeps comparing the same three
# prompts even after src/generation/prompts.py was changed to V2.
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

# V2: strict faithfulness, with a separate-note escape hatch for suspected errors.
PROMPT_V2_STRICT = """Tu es un tuteur de mathématiques pour des élèves de \
Terminale C en Côte d'Ivoire.

Les extraits de cours fournis font autorité (programme officiel). Réponds en \
t'appuyant EXCLUSIVEMENT sur eux.

Règles impératives :
- Rapporte fidèlement ce qu'affirment les extraits, MÊME si cela te semble \
mathématiquement incorrect. Ne corrige JAMAIS un extrait avec tes propres \
connaissances.
- N'ajoute aucun fait, exemple ou formule absent des extraits.
- Cite l'extrait utilisé entre crochets, par exemple [1].
- Si un extrait te paraît erroné, tu peux le signaler dans une note séparée \
à la fin, mais ta réponse principale doit refléter l'extrait, pas ta correction.
- Si les extraits ne permettent pas de répondre, dis-le explicitement."""

# V3: hard faithfulness ceiling — no flagging, no commentary on correctness.
# A PROBE of maximum compliance, NOT a production prompt (you would not ship a
# tutor that silently states false maths). It measures the model's limit.
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

VARIANTS = {
    "V1_lenient": PROMPT_V1_LENIENT,
    "V2_strict": PROMPT_V2_STRICT,
    "V3_hard": PROMPT_V3_HARD,
}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    by_id = {c.metadata.chunk_id: c for c in load_chunks(SUBSET)}
    victim = by_id[POISON_CHUNK_ID]
    poisoned_text = victim.text.replace(r"\le", r"\ge")
    assert poisoned_text != victim.text, (
        rf"poison no-op: '\le' not found in {POISON_CHUNK_ID}"
    )
    poisoned = Chunk(text=poisoned_text, metadata=victim.metadata)
    user = build_user_message(GROUNDING_QUESTION, [poisoned])

    client = ClaudeClient(model="claude-sonnet-4-6")
    print(f"Poisoned {POISON_CHUNK_ID}: |b| <= |a|  ->  |b| >= |a| (FALSE)")
    print(f"QUESTION: {GROUNDING_QUESTION}\n")

    record: dict = {
        "poison_chunk_id": POISON_CHUNK_ID,
        "injected_false_fact": "|b| >= |a| (truth is |b| <= |a|)",
        "question": GROUNDING_QUESTION,
        "variants": {},
    }
    for name, system in VARIANTS.items():
        gen = client.generate(system, user)
        print("=" * 70)
        print(name)
        print("=" * 70)
        print(gen.text)
        print(f"\n(tokens: in={gen.input_tokens} out={gen.output_tokens})\n")
        record["variants"][name] = {
            "answer": gen.text,
            "input_tokens": gen.input_tokens,
            "output_tokens": gen.output_tokens,
        }

    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT.name}")
    print(
        "\nFor each answer ask: does it state |b| >= |a| (FAITHFUL to the poisoned "
        "source) or |b| <= |a| (OVERRIDDEN by the model)? And does it add outside "
        "content despite the instructions?"
    )


if __name__ == "__main__":
    main()