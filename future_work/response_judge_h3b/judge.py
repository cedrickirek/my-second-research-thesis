"""LLM-as-judge for tutor responses — per-criterion scoring (H3, v1).

Scores a (question, response[, reference context]) on the four locked criteria,
1–5 each, by one Claude call constrained to a JSON schema (so the output always
parses). Research-only: the judge is calibrated against the teacher gold and is
never run on students at deployment time.

Model & determinism notes:
- Default model is ``claude-opus-4-8`` (most capable available judge). Opus 4.8
  removed ``temperature`` — we do NOT pass it (passing it would 400). Output is
  constrained by ``output_config.format`` rather than steered by a prefill.
- Opus 4.8 is near- but not bit-deterministic. For calibration, measure judge
  test–retest reliability (run each item ≥2×) rather than assuming determinism;
  that self-consistency number belongs in the H3 write-up (#22–23).

The ``client`` is injectable so unit tests run fully offline with a fake.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from .prompts import build_system_prompt, build_user_message, load_rubric

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 1024

# Locked criteria — order/keys match app.py:RESPONSE_CRITERIA and RUBRIC.md.
CRITERIA: tuple[str, ...] = (
    "factual_accuracy",
    "curriculum_alignment",
    "pedagogical_quality",
    "language_register",
)
SCALE = [1, 2, 3, 4, 5]


def _output_schema() -> dict:
    """JSON schema constraining the response to one {score, justification} per criterion.

    Uses ``enum`` for the score (numeric min/max constraints aren't supported by
    structured outputs); every field required; ``additionalProperties: false``.
    """
    crit = {
        c: {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "enum": SCALE},
                "justification": {"type": "string"},
            },
            "required": ["score", "justification"],
            "additionalProperties": False,
        }
        for c in CRITERIA
    }
    return {
        "type": "object",
        "properties": crit,
        "required": list(CRITERIA),
        "additionalProperties": False,
    }


@dataclass(frozen=True)
class JudgeResult:
    """One judged response: 1–5 per criterion, French justifications, usage."""

    scores: dict[str, int]
    justifications: dict[str, str]
    input_tokens: int
    output_tokens: int
    model: str

    @property
    def mean(self) -> float:
        return sum(self.scores.values()) / len(self.scores)


class ResponseJudge:
    """Scores tutor responses on the four criteria via one constrained Claude call."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        rubric_md: str | None = None,
        client: object | None = None,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._system = build_system_prompt(rubric_md or load_rubric())
        self._schema = _output_schema()
        if client is None:
            from anthropic import Anthropic

            client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
        self._client = client

    def judge(
        self, question: str, response: str, context: str | None = None
    ) -> JudgeResult:
        """Score one tutor response. No temperature (Opus 4.8); schema-constrained."""
        user = build_user_message(question, response, context)
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=self._system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": self._schema}},
        )
        return self._parse(resp)

    def _parse(self, resp: object) -> JudgeResult:
        text = next(
            (b.text for b in resp.content if getattr(b, "type", None) == "text"), ""
        )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:  # schema should prevent this
            raise ValueError(f"judge returned non-JSON output: {text!r}") from exc

        scores, justifications = {}, {}
        for c in CRITERIA:
            block = data.get(c)
            if not isinstance(block, dict) or "score" not in block:
                raise ValueError(f"judge output missing criterion {c!r}: {data!r}")
            score = int(block["score"])
            if score not in SCALE:
                raise ValueError(f"criterion {c!r} score {score} outside 1–5")
            scores[c] = score
            justifications[c] = str(block.get("justification", ""))

        usage = resp.usage
        return JudgeResult(
            scores=scores,
            justifications=justifications,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            model=self._model,
        )
