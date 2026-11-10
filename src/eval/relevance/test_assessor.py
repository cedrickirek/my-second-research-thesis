"""Offline tests for the H3 relevance-assessor (fake client; no API calls)."""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.eval.relevance.assessor import (
    GRADE_FORMAT,
    RelevanceAssessor,
    build_system_prompt,
    parse_response,
    prompt_id,
)


@dataclass
class _Block:
    text: str
    type: str = "text"


@dataclass
class _Usage:
    input_tokens: int = 100
    output_tokens: int = 20
    cache_read_input_tokens: int = 80


@dataclass
class _Resp:
    content: list
    usage: _Usage


class _FakeMessages:
    def __init__(self, payload: dict):
        self._payload = payload
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _Resp(content=[_Block(json.dumps(self._payload))], usage=_Usage())


class _FakeClient:
    def __init__(self, payload: dict):
        self.messages = _FakeMessages(payload)


def test_assess_parses_grade_and_usage():
    client = _FakeClient({"relevance": 2, "rationale": "étape utilisée"})
    a = RelevanceAssessor(client=client)
    out = a.assess("Calcule la limite...", "Propriété: e^x > 0...")
    assert out.relevance == 2
    assert out.rationale == "étape utilisée"
    assert out.input_tokens == 100
    assert out.cache_read_tokens == 80
    assert out.model == "claude-opus-4-8"


def test_request_params_no_temperature_cached_system_structured():
    client = _FakeClient({"relevance": 0, "rationale": "autre sujet"})
    a = RelevanceAssessor(client=client)
    a.assess("q", "c")
    kw = client.messages.last_kwargs
    assert "temperature" not in kw  # Opus 4.8 rejects temperature
    assert kw["model"] == "claude-opus-4-8"
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kw["output_config"]["format"] == GRADE_FORMAT
    # the rubric is embedded in the locked system prompt
    assert "je m'en sers" in kw["system"][0]["text"]


def test_prompt_is_locked_and_hashable():
    p1 = build_system_prompt("RUBRIC A")
    p2 = build_system_prompt("RUBRIC A")
    assert prompt_id(p1) == prompt_id(p2)
    assert prompt_id(p1) != prompt_id(build_system_prompt("RUBRIC B"))


def test_parse_response_handles_missing_cache_field():
    @dataclass
    class _U:
        input_tokens: int = 5
        output_tokens: int = 3

    resp = _Resp(content=[_Block('{"relevance": 3, "rationale": "central"}')], usage=_U())
    out = parse_response(resp, "claude-opus-4-8")
    assert out.relevance == 3
    assert out.cache_read_tokens == 0
