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
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
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


def test_task_crud_lifecycle(client):
    create_response = client.post(
        "/tasks/",
        json={"title": "Review the project", "description": "Check the API"},
    )
    assert create_response.status_code == 200
    created_task = create_response.json()
    task_id = created_task["id"]
    assert created_task["completed"] is False

    list_response = client.get("/tasks/")
    assert list_response.status_code == 200
    assert [task["id"] for task in list_response.json()] == [task_id]

    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Review the project"

    update_response = client.put(
        f"/tasks/{task_id}",
        json={
            "title": "Review the API",
            "description": "Check task endpoints",
            "completed": False,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Review the API"

    complete_response = client.patch(f"/tasks/{task_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["completed"] is True

    delete_response = client.delete(f"/tasks/{task_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["task_id"] == task_id
    assert client.get(f"/tasks/{task_id}").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 201},
    ],
)
def test_create_task_rejects_invalid_title(client, payload):
    response = client.post("/tasks/", json=payload)

    assert response.status_code == 422


def test_create_task_rejects_missing_body(client):
    response = client.post("/tasks/")

    assert response.status_code == 422


def test_task_routes_return_not_found_for_unknown_task(client):
    response = client.get("/tasks/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}