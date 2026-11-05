from fastapi.testclient import TestClient


def create(client: TestClient, **payload: object) -> dict:
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "x-request-id" in response.headers


def test_create_task_defaults_to_todo(client: TestClient) -> None:
    task = create(client, title="Write README")
    assert task["id"] == 1
    assert task["title"] == "Write README"
    assert task["status"] == "todo"
    assert task["description"] is None


def test_create_task_rejects_empty_title(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": ""})
    assert response.status_code == 422


def test_create_task_rejects_unknown_status(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "x", "status": "blocked"})
    assert response.status_code == 422


def test_read_task(client: TestClient) -> None:
    created = create(client, title="Read me", description="details")
    response = client.get(f"/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json()["description"] == "details"


def test_read_missing_task_returns_404(client: TestClient) -> None:
    response = client.get("/tasks/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_list_filters_by_status(client: TestClient) -> None:
    create(client, title="a", status="todo")
    create(client, title="b", status="done")
    create(client, title="c", status="done")

    response = client.get("/tasks", params={"status": "done"})
    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == ["b", "c"]


def test_list_pagination(client: TestClient) -> None:
    for i in range(5):
        create(client, title=f"task {i}")

    response = client.get("/tasks", params={"limit": 2, "offset": 2})
    assert [t["title"] for t in response.json()] == ["task 2", "task 3"]


def test_list_rejects_bad_limit(client: TestClient) -> None:
    assert client.get("/tasks", params={"limit": 0}).status_code == 422
    assert client.get("/tasks", params={"limit": 101}).status_code == 422


def test_patch_updates_only_sent_fields(client: TestClient) -> None:
    created = create(client, title="Original", description="keep me")

    response = client.patch(f"/tasks/{created['id']}", json={"status": "in_progress"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["title"] == "Original"
    assert body["description"] == "keep me"
    assert body["updated_at"] >= body["created_at"]


def test_patch_can_clear_description(client: TestClient) -> None:
    created = create(client, title="t", description="remove me")
    response = client.patch(f"/tasks/{created['id']}", json={"description": None})
    assert response.status_code == 200
    assert response.json()["description"] is None


def test_patch_rejects_null_title(client: TestClient) -> None:
    created = create(client, title="t")
    response = client.patch(f"/tasks/{created['id']}", json={"title": None})
    assert response.status_code == 422


def test_patch_missing_task_returns_404(client: TestClient) -> None:
    response = client.patch("/tasks/999", json={"title": "x"})
    assert response.status_code == 404


def test_delete_task(client: TestClient) -> None:
    created = create(client, title="Delete me")
    assert client.delete(f"/tasks/{created['id']}").status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404
    assert client.delete(f"/tasks/{created['id']}").status_code == 404
