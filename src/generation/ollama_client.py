"""Thin Ollama client wrapper mirroring ClaudeClient's interface.

The H4 hypothesis ("grounding closes the frontier-vs-SLM gap") needs a small
open-weight model (the SLM) to generate alongside the frontier Claude model.
This wraps a locally-served Ollama model behind the SAME generate(system, user)
-> Generation contract as src.generation.client.ClaudeClient, so the H4 runner
calls one interface and only the backend differs.

Talks to the local Ollama HTTP server (default http://localhost:11434). Uses
the /api/chat endpoint with stream=False for a single, bounded response.
Temperature defaults to 0 and the seed is fixed for near-deterministic,
reproducible eval output — matching the Claude side. Token counts come from
Ollama's prompt_eval_count / eval_count fields (for cost/length transparency in
logs; local inference is free but the numbers keep the record shape identical).
"""

from __future__ import annotations

import json
import urllib.request

from src.generation.client import Generation

DEFAULT_MODEL = "mistral:7b"
DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.0
DEFAULT_SEED = 42


class OllamaClient:
    """Wraps a locally-served Ollama model for a single grounded generation."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        seed: int = DEFAULT_SEED,
        timeout: float = 600.0,
    ) -> None:
        self._model = model
        self._host = host.rstrip("/")
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._seed = seed
        self._timeout = timeout

    def generate(self, system: str, user: str) -> Generation:
        """Make exactly one Ollama /api/chat call and return text + token usage."""
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "temperature": self._temperature,
                "seed": self._seed,
                "num_predict": self._max_tokens,
            },
        }
        req = urllib.request.Request(
            f"{self._host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        text = body["message"]["content"]
        return Generation(
            text=text,
            input_tokens=int(body.get("prompt_eval_count", 0)),
            output_tokens=int(body.get("eval_count", 0)),
            model=self._model,
        )