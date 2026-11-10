"""French tutor prompt: system instructions + retrieved-context formatting.

Pure data and string assembly — no API calls, no I/O, so it is fully unit
tested offline. The system prompt is in French (per repo convention) and is
deliberately strict about *source-faithfulness*: the model must report the
extracts verbatim even when they look wrong, and may only flag a suspected
error in a separate note — never silently correct the source from its own
knowledge. This is the "V2" prompt selected by the ablation in
experiments/2026-06-01-baseline-smoke-test/prompt_ablation.py: a looser prompt
overrode a deliberately corrupted extract and mis-attributed the correction to
the source, whereas this version reports faithfully while surfacing the
suspected error for human adjudication.
"""

from __future__ import annotations

from src.corpus.metadata import Chunk

SYSTEM_PROMPT = """Tu es un tuteur de mathématiques pour des élèves de \
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


def build_user_message(question: str, passages: list[Chunk]) -> str:
    """Assemble the user turn: numbered context extracts + the question.

    Passages are numbered [1], [2], ... in order. The caller keeps the mapping
    from each number back to its chunk_id (for the grounding check and logging);
    the prompt itself stays student-appropriate and does not expose chunk ids.
    """
    blocks = [f"[{i}] {c.text}" for i, c in enumerate(passages, 1)]
    context = "\n\n".join(blocks)
    return f"Extraits de cours :\n\n{context}\n\nQuestion de l'élève : {question}"