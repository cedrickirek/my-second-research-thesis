"""Offline tests for the response judge — no network, fake Anthropic client."""

from __future__ import annotations

import json

import pytest

from .judge import CRITERIA, SCALE, ResponseJudge, _output_schema
from .prompts import build_user_message


# --- fake Anthropic client ------------------------------------------------


class _Block:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _Usage:
    input_tokens = 123
    output_tokens = 45


class _Resp:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]
        self.usage = _Usage()


class _Messages:
    def __init__(self, outer: "FakeClient") -> None:
        self._outer = outer

    def create(self, **kwargs):
        self._outer.last_kwargs = kwargs
        return _Resp(self._outer.payload)


class FakeClient:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.last_kwargs = None
        self.messages = _Messages(self)


def _payload(scores: dict[str, int]) -> str:
    return json.dumps(
        {c: {"score": scores[c], "justification": f"ok-{c}"} for c in CRITERIA}
    )


# --- tests ----------------------------------------------------------------


def test_judge_parses_scores_and_justifications():
    fake = FakeClient(_payload({c: 4 for c in CRITERIA}))
    judge = ResponseJudge(client=fake)
    res = judge.judge("Question ?", "Une réponse.")
    assert res.scores == {c: 4 for c in CRITERIA}
    assert res.justifications["factual_accuracy"] == "ok-factual_accuracy"
    assert res.mean == 4.0
    assert (res.input_tokens, res.output_tokens) == (123, 45)


def test_judge_omits_temperature_and_sets_schema():
    fake = FakeClient(_payload({c: 3 for c in CRITERIA}))
    ResponseJudge(client=fake, model="claude-opus-4-8").judge("Q", "R")
    kw = fake.last_kwargs
    assert "temperature" not in kw  # Opus 4.8 would 400 on temperature
    assert kw["model"] == "claude-opus-4-8"
    assert kw["output_config"]["format"]["type"] == "json_schema"


def test_schema_shape():
    schema = _output_schema()
    assert set(schema["required"]) == set(CRITERIA)
    assert schema["additionalProperties"] is False
    for c in CRITERIA:
        assert schema["properties"][c]["properties"]["score"]["enum"] == SCALE


def test_context_included_only_when_present():
    assert "PASSAGES DE RÉFÉRENCE" not in build_user_message("Q", "R")
    assert "PASSAGES DE RÉFÉRENCE" in build_user_message("Q", "R", context="Théorème X")


def test_out_of_range_score_rejected():
    fake = FakeClient(_payload({**{c: 3 for c in CRITERIA}, "factual_accuracy": 6}))
    with pytest.raises(ValueError, match="outside"):
        ResponseJudge(client=fake).judge("Q", "R")


def test_missing_criterion_rejected():
    bad = json.dumps({"factual_accuracy": {"score": 3, "justification": "x"}})
    with pytest.raises(ValueError, match="missing criterion"):
        ResponseJudge(client=FakeClient(bad)).judge("Q", "R")
