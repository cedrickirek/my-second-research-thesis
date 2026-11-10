"""Unit tests for the Claude client wrapper, using a fake SDK client (offline).

No API key and no network are needed: a fake stands in for anthropic.Anthropic.

Run: uv run pytest src/generation/ -q
"""

from src.generation.client import ClaudeClient, Generation


class _FakeBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeUsage:
    input_tokens = 123
    output_tokens = 45


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.content = [_FakeBlock(text)]
        self.usage = _FakeUsage()


class _FakeMessages:
    def __init__(self, recorder: dict) -> None:
        self._recorder = recorder

    def create(self, **kwargs):
        self._recorder.update(kwargs)
        return _FakeResponse("Réponse de test [1].")


class _FakeAnthropic:
    def __init__(self) -> None:
        self.calls: dict = {}
        self.messages = _FakeMessages(self.calls)


def test_generate_returns_text_and_usage():
    g = ClaudeClient(client=_FakeAnthropic()).generate("sys", "user")
    assert isinstance(g, Generation)
    assert g.text == "Réponse de test [1]."
    assert g.input_tokens == 123 and g.output_tokens == 45
    assert g.model == "claude-sonnet-4-6"


def test_generate_passes_system_messages_and_token_cap():
    fake = _FakeAnthropic()
    ClaudeClient(client=fake, max_tokens=512).generate("SYS", "USR")
    assert fake.calls["model"] == "claude-sonnet-4-6"
    assert fake.calls["max_tokens"] == 512
    assert fake.calls["system"] == "SYS"
    assert fake.calls["messages"] == [{"role": "user", "content": "USR"}]
    assert fake.calls["temperature"] == 0.0  # default: reproducible eval runs
