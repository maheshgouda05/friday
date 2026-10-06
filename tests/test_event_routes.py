import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app


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


def test_event_crud_lifecycle(client):
    create_response = client.post(
        "/events/",
        json={
            "title": "DBMS exam",
            "date": "2026-10-12",
            "time": "09:30:00",
            "event_type": "exam",
            "location": "Room 12",
        },
    )
    assert create_response.status_code == 201
    created_event = create_response.json()
    event_id = created_event["id"]
    assert created_event["status"] == "upcoming"

    assert client.get("/events/").json()[0]["id"] == event_id
    assert client.get(f"/events/{event_id}").json()["title"] == "DBMS exam"

    update_response = client.put(
        f"/events/{event_id}",
        json={"title": "DBMS final exam", "status": "completed"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "DBMS final exam"
    assert update_response.json()["status"] == "completed"

    unconfirmed_delete = client.delete(f"/events/{event_id}")
    assert unconfirmed_delete.status_code == 409
    assert client.get(f"/events/{event_id}").status_code == 200

    delete_response = client.delete(f"/events/{event_id}?confirm=true")
    assert delete_response.status_code == 200
    assert client.get(f"/events/{event_id}").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": "Exam"},
        {"title": "   ", "date": "2026-10-12"},
        {"title": "Exam", "date": "not-a-date"},
        {"title": "Exam", "date": "2026-10-12", "event_type": "unknown"},
    ],
)
def test_create_event_rejects_invalid_input(client, payload):
    response = client.post("/events/", json=payload)

    assert response.status_code == 422


def test_update_event_rejects_empty_body(client):
    create_response = client.post(
        "/events/",
        json={"title": "Exam", "date": "2026-10-12"},
    )
    event_id = create_response.json()["id"]

    response = client.put(f"/events/{event_id}", json={})

    assert response.status_code == 422


def test_event_routes_return_not_found_for_unknown_event(client):
    response = client.get("/events/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found"}