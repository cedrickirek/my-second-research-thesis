"""Thin Anthropic client wrapper for the RAG generator.

Reads the API key from the ANTHROPIC_API_KEY environment variable (never
hard-coded, never written to disk, never printed). Makes exactly one message
request per call — no loops, no retries-in-loop — caps output with max_tokens
so cost is bounded, and defaults to temperature=0 for near-deterministic,
reproducible output on evaluation runs.

The underlying client is injectable so unit tests run offline with a fake;
production passes None and a real anthropic.Anthropic() is created lazily.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.0  # near-deterministic output for reproducible eval runs


@dataclass(frozen=True)
class Generation:
    """One model response plus token usage (for cost transparency in logs)."""

    text: str
    input_tokens: int
    output_tokens: int
    model: str


class ClaudeClient:
    """Wraps anthropic.Anthropic for a single grounded generation call."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        client: object | None = None,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        if client is None:
            from anthropic import Anthropic

            client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
        self._client = client

    def generate(self, system: str, user: str) -> Generation:
        """Make exactly one Claude call and return its text + token usage."""
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        return Generation(
            text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            model=self._model,
        )