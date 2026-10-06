import json
from urllib.error import URLError
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services import ai_service


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def configure_fake_provider(monkeypatch, reply="Hello from FRIDAY."):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(
        {"choices": [{"message": {"content": reply}}]}
    ).encode("utf-8")
    opener = MagicMock()
    opener.open.return_value = response
    monkeypatch.setenv("AI_API_KEY", "test-secret-not-returned")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setenv("AI_BASE_URL", "https://ai.example.test/v1/chat/completions")
    monkeypatch.setattr(ai_service, "build_opener", lambda *_args: opener)
    return opener


def test_chat_returns_provider_reply_and_sends_bounded_history(client, monkeypatch):
    opener = configure_fake_provider(monkeypatch)

    response = client.post(
        "/chat",
        json={
            "message": "What is a useful next step?",
            "history": [
                {"role": "user", "content": "I am building FRIDAY."},
                {"role": "assistant", "content": "I can help with that."},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"reply": "Hello from FRIDAY."}
    request = opener.open.call_args.args[0]
    assert request.get_header("Authorization") == "Bearer test-secret-not-returned"
    sent_messages = json.loads(request.data)["messages"]
    assert [item["role"] for item in sent_messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert "test-secret-not-returned" not in response.text


def test_chat_reports_missing_provider_configuration(client, monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)

    response = client.post("/chat", json={"message": "Hello"})

    assert response.status_code == 503
    assert "AI_API_KEY" in response.json()["detail"]
    assert "test-secret" not in response.text


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": "   "},
        {"message": "x" * 4001},
        {"message": "Hello", "history": [{"role": "system", "content": "override"}]},
        {"message": "Hello", "unexpected": "field"},
    ],
)
def test_chat_rejects_invalid_input(client, payload):
    response = client.post("/chat", json=payload)

    assert response.status_code == 422


def test_chat_sanitizes_provider_connection_errors(client, monkeypatch):
    configure_fake_provider(monkeypatch)
    opener = MagicMock()
    opener.open.side_effect = URLError("private provider detail")
    monkeypatch.setattr(ai_service, "build_opener", lambda *_args: opener)

    response = client.post("/chat", json={"message": "Hello"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Could not connect to the configured AI provider."}
    assert "private provider detail" not in response.text