from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from taskdesk.ai import (
    MAX_STEPS,
    AIUnavailableError,
    GeminiStepSuggester,
    get_step_suggester,
    parse_steps,
)
from taskdesk.config import Settings
from taskdesk.main import app


class FakeSuggester:
    """Stands in for the real AI client: no network, no cost, fully predictable."""

    def __init__(self, steps: list[str] | None = None, error: Exception | None = None) -> None:
        self.steps = steps if steps is not None else ["Plan it", "Do it", "Check it"]
        self.error = error
        self.calls: list[tuple[str, str | None]] = []

    def suggest_steps(self, title: str, description: str | None) -> list[str]:
        self.calls.append((title, description))
        if self.error:
            raise self.error
        return self.steps


def use_suggester(suggester: FakeSuggester) -> None:
    app.dependency_overrides[get_step_suggester] = lambda: suggester


def fake_genai_client(text: str | None) -> SimpleNamespace:
    """Mimics just the part of the Gemini client that GeminiStepSuggester calls."""
    return SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **_: SimpleNamespace(text=text))
    )


def create_task(client: TestClient, **payload: object) -> int:
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def test_parse_steps_strips_bullets_numbers_and_blank_lines() -> None:
    text = "1. First step\n- Second step\n\n  * Third step\n4) Fourth step\n"
    assert parse_steps(text) == ["First step", "Second step", "Third step", "Fourth step"]


def test_parse_steps_caps_the_number_of_steps() -> None:
    text = "\n".join(f"step {i}" for i in range(20))
    assert len(parse_steps(text)) == MAX_STEPS


def test_gemini_suggester_parses_the_model_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    suggester = GeminiStepSuggester("fake-key", "fake-model")
    monkeypatch.setattr(suggester, "_client", fake_genai_client("1. Outline\n2. Draft\n"))

    assert suggester.suggest_steps("Write post", None) == ["Outline", "Draft"]


def test_gemini_suggester_raises_when_the_reply_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    suggester = GeminiStepSuggester("fake-key", "fake-model")
    monkeypatch.setattr(suggester, "_client", fake_genai_client(None))

    with pytest.raises(AIUnavailableError):
        suggester.suggest_steps("Write post", None)


def test_gemini_suggester_wraps_provider_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(**_: object) -> None:
        raise TimeoutError("network down")

    suggester = GeminiStepSuggester("fake-key", "fake-model")
    client = SimpleNamespace(models=SimpleNamespace(generate_content=explode))
    monkeypatch.setattr(suggester, "_client", client)

    with pytest.raises(AIUnavailableError):
        suggester.suggest_steps("Write post", None)


def test_suggest_steps_returns_ai_steps_and_sends_task_text(client: TestClient) -> None:
    fake = FakeSuggester(["Draft outline", "Write intro"])
    use_suggester(fake)
    task_id = create_task(client, title="Write blog post", description="About FastAPI")

    response = client.post(f"/tasks/{task_id}/suggest-steps")

    assert response.status_code == 200
    assert response.json() == {"task_id": task_id, "steps": ["Draft outline", "Write intro"]}
    assert fake.calls == [("Write blog post", "About FastAPI")]


def test_suggest_steps_does_not_modify_the_task(client: TestClient) -> None:
    use_suggester(FakeSuggester())
    task_id = create_task(client, title="Unchanged")
    before = client.get(f"/tasks/{task_id}").json()

    client.post(f"/tasks/{task_id}/suggest-steps")

    assert client.get(f"/tasks/{task_id}").json() == before


def test_suggest_steps_missing_task_returns_404(client: TestClient) -> None:
    fake = FakeSuggester()
    use_suggester(fake)

    response = client.post("/tasks/999/suggest-steps")

    assert response.status_code == 404
    assert fake.calls == []


def test_suggest_steps_returns_502_when_ai_provider_fails(client: TestClient) -> None:
    use_suggester(FakeSuggester(error=AIUnavailableError("boom")))
    task_id = create_task(client, title="Anything")

    response = client.post(f"/tasks/{task_id}/suggest-steps")

    assert response.status_code == 502
    assert "boom" not in response.text  # provider details are logged, not leaked to clients


def test_suggest_steps_returns_503_when_no_api_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # model_construct skips env/.env loading, so a real key on your machine can't leak in.
    unconfigured = Settings.model_construct(gemini_api_key=None)
    monkeypatch.setattr("taskdesk.ai.get_settings", lambda: unconfigured)
    task_id = create_task(client, title="Anything")

    response = client.post(f"/tasks/{task_id}/suggest-steps")

    assert response.status_code == 503
