"""Prompt construction for the LLM-as-judge (response scoring, H3).

The judge scores a tutor *response* on the four locked criteria (see
``RUBRIC.md`` and ``app.py:RESPONSE_CRITERIA``) on a 1–5 scale. The rubric text
is loaded from ``RUBRIC.md`` at call time and injected into the system prompt, so
there is a single source of truth for the descriptors (edit the rubric, not a
copy here).

Variant-blind by construction: the judge is never told which retriever or
generator produced the response, so its scores can't be biased by the system
under test. The optional reference context is the *retrieved curriculum* passages
the answer was meant to be grounded in — supply it so the judge can assess
factual accuracy and curriculum alignment against the syllabus, not only its own
priors (that grounding is the point of H3).
"""

from __future__ import annotations

from pathlib import Path

RUBRIC_PATH = Path(__file__).resolve().parent / "RUBRIC.md"

SYSTEM_PROMPT_TEMPLATE = """Tu es un professeur de mathématiques expérimenté, \
correcteur au baccalauréat ivoirien, série C. Tu évalues la réponse d'un tuteur \
à une question d'un élève de Terminale C.

Évalue la réponse selon les QUATRE critères de la rubrique ci-dessous, chacun \
noté de 1 à 5. Règles impératives :
- Note chaque critère INDÉPENDAMMENT des autres.
- Une réponse fluide mais mathématiquement FAUSSE doit recevoir une note basse \
en exactitude factuelle, indépendamment de la qualité de rédaction.
- Sois exigeant et impartial ; n'accorde pas le bénéfice du doute.
- Appuie-toi sur les passages de référence du programme s'ils sont fournis.

RUBRIQUE :
{rubric}

Pour CHAQUE critère, donne une note entière de 1 à 5 et une justification d'UNE \
phrase en français."""


def load_rubric(path: Path | str = RUBRIC_PATH) -> str:
    """Read the response rubric markdown (single source of truth for descriptors)."""
    return Path(path).read_text(encoding="utf-8").strip()


def build_system_prompt(rubric_md: str | None = None) -> str:
    """System prompt with the rubric injected. Loads RUBRIC.md if not given."""
    return SYSTEM_PROMPT_TEMPLATE.format(rubric=rubric_md or load_rubric())


def build_user_message(question: str, response: str, context: str | None = None) -> str:
    """The (question, [reference context], response) block to be scored."""
    parts = [f"QUESTION DE L'ÉLÈVE :\n{question.strip()}"]
    if context and context.strip():
        parts.append(
            "PASSAGES DE RÉFÉRENCE (programme Terminale C) :\n" + context.strip()
        )
    parts.append(f"RÉPONSE DU TUTEUR À ÉVALUER :\n{response.strip()}")
    return "\n\n".join(parts)
