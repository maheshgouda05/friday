from datetime import datetime, timezone
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.services import conversation_service, title_service
from backend.services.ai_service import AIServiceError


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_conversation_persists_messages_context_title_and_timestamps(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        title_service,
        "generate_conversation_title",
        lambda _message: "DBMS Exam Preparation",
    )
    seen_context = []

    def fake_reply(message, history, context=None):
        seen_context.append((message, [(turn.role, turn.content) for turn in history]))
        return "Let's review normalization first." if len(seen_context) == 1 else "We were discussing normalization."

    monkeypatch.setattr(conversation_service, "generate_reply", fake_reply)

    created = client.post("/conversations")
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    assert created.json()["title"] == "New Chat"

    first_message = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "I have a DBMS exam and need to study."},
    )
    assert first_message.status_code == 201
    assert first_message.json()["conversation"]["title"] == "DBMS Exam Preparation"
    assert first_message.json()["reply"] == "Let's review normalization first."

    second_message = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "Continue with that."},
    )
    assert second_message.status_code == 201
    assert seen_context[1] == (
        "Continue with that.",
        [
            ("user", "I have a DBMS exam and need to study."),
            ("assistant", "Let's review normalization first."),
        ],
    )

    detail = client.get(f"/conversations/{conversation_id}")
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    created_at = datetime.fromisoformat(detail.json()["created_at"])
    assert created_at.tzinfo is not None
    assert created_at.utcoffset() == timezone.utc.utcoffset(created_at)
    assert datetime.fromisoformat(detail.json()["last_message_at"]) >= created_at


def test_new_conversation_is_independent_and_archiving_preserves_history(client):
    first = client.post("/conversations").json()
    client.post(
        f"/conversations/{first['id']}/messages",
        json={"content": "Plan the old project."},
    )
    second = client.post("/conversations").json()
    assert first["id"] != second["id"]
    assert client.get("/conversations").json()[0]["id"] == second["id"]

    archived = client.delete(f"/conversations/{first['id']}")
    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert [item["id"] for item in client.get("/conversations").json()] == [second["id"]]
    assert client.get("/conversations?archived=true").json()[0]["id"] == first["id"]
    assert client.get(f"/conversations/{first['id']}").status_code == 200
    assert client.post(
        f"/conversations/{first['id']}/messages",
        json={"content": "This is archived."},
    ).status_code == 409


def test_conversation_title_can_be_updated(client):
    conversation = client.post("/conversations").json()

    response = client.patch(
        f"/conversations/{conversation['id']}",
        json={"title": "Weekly Planning"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Weekly Planning"


def test_schedule_question_answers_from_saved_event_without_ai(client, monkeypatch):
    tomorrow = (datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=1)).isoformat()
    event_response = client.post(
        "/events/",
        json={
            "title": "DBMS exam",
            "date": tomorrow,
            "time": "09:30:00",
            "event_type": "exam",
        },
    )
    assert event_response.status_code == 201
    monkeypatch.setattr(title_service, "generate_conversation_title", lambda _message: "Tomorrow Schedule")
    monkeypatch.setattr(
        conversation_service,
        "generate_reply",
        lambda *_args: (_ for _ in ()).throw(AssertionError("AI should not be required")),
    )
    conversation_id = client.post("/conversations").json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "What do I have tomorrow?"},
    )

    assert response.status_code == 201
    assert response.json()["reply"] == "You have DBMS exam at 9:30 AM tomorrow."
    assert response.json()["conversation"]["title"] == "Tomorrow Schedule"


def test_relevant_event_context_is_sent_to_ai(client, monkeypatch):
    tomorrow = (datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=1)).isoformat()
    client.post(
        "/events/",
        json={"title": "DBMS exam", "date": tomorrow, "event_type": "exam"},
    )
    monkeypatch.setattr(title_service, "generate_conversation_title", lambda _message: "Exam Preparation")
    captured = {}

    def fake_reply(message, history, context):
        captured.update(message=message, history=history, context=context)
        return "We can make a short revision plan."

    monkeypatch.setattr(conversation_service, "generate_reply", fake_reply)
    conversation_id = client.post("/conversations").json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "I am nervous about my DBMS exam tomorrow."},
    )

    assert response.status_code == 201
    assert '"timezone": "Asia/Kolkata"' in captured["context"]
    assert '"title": "DBMS exam"' in captured["context"]
    assert '"period": "tomorrow"' in captured["context"]


def test_provider_failure_keeps_user_message_and_saves_friendly_reply(
    client,
    monkeypatch,
):
    monkeypatch.setattr(title_service, "generate_conversation_title", lambda _message: "Project Planning")
    monkeypatch.setattr(
        conversation_service,
        "generate_reply",
        lambda _message, _history, _context: (_ for _ in ()).throw(AIServiceError("internal error", 503)),
    )
    conversation_id = client.post("/conversations").json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "Help me plan my project."},
    )

    assert response.status_code == 201
    assert response.json()["user_message"]["content"] == "Help me plan my project."
    assert "message is still saved" in response.json()["reply"]
    assert len(client.get(f"/conversations/{conversation_id}").json()["messages"]) == 2


def test_conversation_endpoints_validate_ids_and_messages(client):
    assert client.get("/conversations/not-a-uuid").status_code == 422
    assert client.get("/conversations/00000000-0000-0000-0000-000000000000").status_code == 404

    conversation_id = client.post("/conversations").json()["id"]
    assert client.post(f"/conversations/{conversation_id}/messages", json={}).status_code == 422
    assert client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "   "},
    ).status_code == 422


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("I have a DBMS exam tomorrow and need to study tonight.", "DBMS Exam Study"),
        ("Help me plan my week", "Plan Week"),
        ("What do I have tomorrow?", "Tomorrow Schedule"),
        ("Database design", "Database Design Discussion"),
        ("Hey", "General Conversation"),
    ],
)
def test_fallback_title_is_short_and_not_the_full_message(message, expected, monkeypatch):
    monkeypatch.setattr(
        title_service,
        "generate_conversation_title",
        lambda _message: (_ for _ in ()).throw(AIServiceError("not configured", 503)),
    )

    title = title_service.generate_title(message)

    assert title == expected
    assert len(title.split()) <= 5