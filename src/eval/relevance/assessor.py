"""LLM relevance-assessor for the reframed H3 — scores (query, chunk) on the 0-3 rubric.

Each (query, chunk) pair is scored on the SAME 0-3 relevance rubric the human
panel used (`RUBRIC.md`), prompted with the rubric itself, so human and machine
judge against the same definition of relevance (§M9.2). The assessor's labels
("LLM qrels") are used ONLY to validate the assessor (ranking agreement + per-item
agreement, §M9.4/M9.5) — never to conclude H1/H2, which stay on the human qrels
(circularity firewall, §M9.6).

Model = Claude Opus 4.8, the most capable judge here. It exposes **no**
`temperature` parameter (passing one is a 400), so reproducibility is established
by **test-retest reliability** (>=2 runs per item, self-consistency reported), not
by temp-0 (§M9.2; decision 2026-06-26). The prompt is **locked**: its sha256
(`prompt_id`) is recorded with every run, and the exact text goes to the annex.

The Anthropic client is injectable so tests run offline with a fake.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

MODEL = "claude-opus-4-8"  # no temperature param; reproducibility via test-retest
MAX_TOKENS = 512
# v1.1 = v1.0 written rubric + the verbal dispatch clarifications written down
# (chapter-level topic floor: same-chapter-unused -> 1; partial/method utility -> 2;
# full coverage -> 3). The assessor judges by the same definition the panel applied.
RUBRIC_VERSION = "v1.1"
RUBRIC_PATH = Path(__file__).with_name("RUBRIC_v1.1.md")

# Structured output: a single 0-3 grade plus a one-sentence rationale. `enum`
# guarantees a parseable score (numeric range constraints aren't supported, but
# enum is) — see the claude-api structured-outputs limitations.
GRADE_FORMAT = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "relevance": {"type": "integer", "enum": [0, 1, 2, 3]},
            "rationale": {"type": "string"},
        },
        "required": ["relevance", "rationale"],
        "additionalProperties": False,
    },
}


def build_system_prompt(rubric_text: str) -> str:
    """The locked instruction: the human rubric verbatim + the grading task (FR)."""
    return (
        "Tu es enseignant(e) de mathématiques de Terminale C (Côte d'Ivoire) et tu "
        "annotes la pertinence de passages de cours retrouvés pour des questions "
        "d'élèves, exactement selon la rubrique ci-dessous.\n\n"
        f"{rubric_text}\n\n"
        "Pour la paire (question, passage) fournie, attribue UNE note de pertinence "
        "de 0 à 3 en appliquant la « question à se poser », le test « je m'en sers » "
        "et les règles de décision ci-dessus. Juge ce passage précis pour cette "
        "question précise (pas le chapitre en général). Donne une justification "
        "brève (une phrase)."
    )


def build_user_prompt(query_text: str, chunk_text: str) -> str:
    return (
        f"QUESTION DE L'ÉLÈVE :\n{query_text}\n\n"
        f"PASSAGE DU COURS RETROUVÉ :\n{chunk_text}\n\n"
        "Attribue la note de pertinence (0–3) à ce passage pour cette question."
    )


def load_system_prompt() -> str:
    return build_system_prompt(RUBRIC_PATH.read_text(encoding="utf-8"))


def prompt_id(system_prompt: str) -> str:
    """Short stable hash of the locked prompt, recorded with every run."""
    return hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Assessment:
    relevance: int
    rationale: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    model: str


def parse_response(resp: object, model: str) -> Assessment:
    """Parse a Messages API response (structured output) into an Assessment."""
    text = "".join(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    u = resp.usage
    return Assessment(
        relevance=int(data["relevance"]),
        rationale=str(data.get("rationale", "")),
        input_tokens=getattr(u, "input_tokens", 0),
        output_tokens=getattr(u, "output_tokens", 0),
        cache_read_tokens=(getattr(u, "cache_read_input_tokens", 0) or 0),
        model=model,
    )


class RelevanceAssessor:
    """Scores one (query, chunk) pair on the 0-3 rubric with Claude (no temperature)."""

    def __init__(
        self,
        system_prompt: str | None = None,
        client: object | None = None,
        model: str = MODEL,
        max_tokens: int = MAX_TOKENS,
    ) -> None:
        self.system_prompt = system_prompt or load_system_prompt()
        self._model = model
        self._max_tokens = max_tokens
        self._client = client  # lazily created on first real call (see _api)

    @property
    def prompt_id(self) -> str:
        return prompt_id(self.system_prompt)

    @property
    def model(self) -> str:
        return self._model

    def request_params(self, query_text: str, chunk_text: str) -> dict:
        """Exact Messages-API params for one pair — reused verbatim by the batch runner.

        The rubric system prompt is identical across all pairs, so it carries a
        `cache_control` breakpoint: it is written once and read at ~0.1x cost on
        every subsequent pair, which is the bulk of the savings on this run.
        """
        return {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": [
                {
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [
                {"role": "user", "content": build_user_prompt(query_text, chunk_text)}
            ],
            "output_config": {"format": GRADE_FORMAT},
        }

    def _api(self) -> object:
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
        return self._client

    def assess(self, query_text: str, chunk_text: str) -> Assessment:
        """One paid Claude call scoring a single (query, chunk) pair."""
        resp = self._api().messages.create(**self.request_params(query_text, chunk_text))
        return parse_response(resp, self._model)
