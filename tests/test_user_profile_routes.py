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


def test_profile_create_read_update_lifecycle(client):
    create_response = client.post(
        "/profile",
        json={
            "name": "Mahesh",
            "preferred_name": "M",
            "timezone": "Asia/Kolkata",
            "daily_wake_time": "07:00:00",
            "usual_sleep_time": "23:00:00",
            "interests": ["Python", "Music"],
            "learning_goals": ["FastAPI"],
            "personal_goals": ["Exercise regularly"],
            "communication_style": "Concise and practical",
        },
    )
    assert create_response.status_code == 201
    created_profile = create_response.json()
    assert created_profile["name"] == "Mahesh"
    assert created_profile["interests"] == ["Python", "Music"]

    read_response = client.get("/profile")
    assert read_response.status_code == 200
    assert read_response.json()["timezone"] == "Asia/Kolkata"

    update_response = client.patch(
        "/profile",
        json={"preferred_name": "Mahi", "interests": []},
    )
    assert update_response.status_code == 200
    assert update_response.json()["preferred_name"] == "Mahi"
    assert update_response.json()["interests"] == []

    duplicate_response = client.post(
        "/profile",
        json={"name": "Another user", "timezone": "UTC"},
    )
    assert duplicate_response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"timezone": "UTC"},
        {"name": "Mahesh"},
        {"name": "Mahesh", "timezone": "Not/A_Timezone"},
        {"name": "   ", "timezone": "UTC"},
        {"name": "Mahesh", "timezone": "UTC", "interests": [""]},
    ],
)
def test_create_profile_rejects_invalid_input(client, payload):
    response = client.post("/profile", json=payload)

    assert response.status_code == 422


def test_profile_routes_return_not_found_when_profile_is_missing(client):
    assert client.get("/profile").status_code == 404
    assert client.patch("/profile", json={"preferred_name": "M"}).status_code == 404


def test_profile_update_rejects_empty_or_invalid_body(client):
    client.post("/profile", json={"name": "Mahesh", "timezone": "UTC"})

    assert client.patch("/profile", json={}).status_code == 422
    assert client.patch("/profile", json={"name": None}).status_code == 422