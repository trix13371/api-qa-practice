import pytest


def test_create_task_and_read_it_back(api_url, http):
    # Arrange: the new server has no tasks.
    initial_response = http.get(f"{api_url}/tasks", timeout=3)
    assert initial_response.status_code == 200
    assert initial_response.json() == []
    title = "Learn API"

    # Act: create a task through HTTP.
    create_response = http.post(
        f"{api_url}/tasks", json={"title": title}, timeout=3
    )

    # Assert: check both the response and the saved data.
    assert create_response.status_code == 201
    assert create_response.headers["Content-Type"].startswith("application/json")
    task = create_response.json()
    assert type(task["id"]) is int
    assert task["id"] > 0
    expected_task = {"id": task["id"], "title": title, "completed": False}
    assert task == expected_task

    list_response = http.get(f"{api_url}/tasks", timeout=3)
    assert list_response.status_code == 200
    assert list_response.json() == [expected_task]

    detail_response = http.get(f"{api_url}/tasks/{task['id']}", timeout=3)
    assert detail_response.status_code == 200
    assert detail_response.json() == expected_task


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"title": 123}, {}],
    ids=["empty-title", "numeric-title", "missing-title"],
)
def test_invalid_task_does_not_change_saved_tasks(api_url, http, payload):
    # Arrange: an existing task must survive a rejected request.
    existing_response = http.post(
        f"{api_url}/tasks", json={"title": "Keep this task"}, timeout=3
    )
    assert existing_response.status_code == 201
    before_response = http.get(f"{api_url}/tasks", timeout=3)
    assert before_response.status_code == 200
    saved_tasks = before_response.json()
    assert saved_tasks == [existing_response.json()]

    # Act: send one invalid payload.
    response = http.post(f"{api_url}/tasks", json=payload, timeout=3)

    # Assert: rejection must not create or erase tasks.
    assert response.status_code == 400
    assert response.headers["Content-Type"].startswith("application/json")
    assert response.json() == {"error": "title must be a non-empty string"}

    after_response = http.get(f"{api_url}/tasks", timeout=3)
    assert after_response.status_code == 200
    assert after_response.json() == saved_tasks
