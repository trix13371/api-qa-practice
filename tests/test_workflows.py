"""Business workflows, owner isolation, validation and stable pagination."""
import pytest

from storage import get_db


def create_task(http, api_url, title="Review requirements"):
    response = http.post(f"{api_url}/tasks", json={"title": title}, timeout=3)
    assert response.status_code == 201, response.text
    return response.json()


def test_task_full_lifecycle(api_url, http):
    task = create_task(http, api_url)
    url = f"{api_url}/tasks/{task['id']}"
    for patch in [{"title": "Updated title"}, {"completed": True},
                  {"title": "Reopened", "completed": False}]:
        response = http.patch(url, json=patch, timeout=3)
        assert response.status_code == 200
        task.update(patch)
        assert response.json() == task
        assert http.get(url, timeout=3).json() == task
    response = http.delete(url, timeout=3)
    assert response.status_code == 204
    assert response.content == b""
    assert http.get(url, timeout=3).status_code == 404
    assert http.delete(url, timeout=3).status_code == 404
    assert http.get(f"{api_url}/tasks", timeout=3).json() == []


def test_users_cannot_read_or_change_each_others_tasks(api_url, http, login_as, app):
    owner_task = create_task(http, api_url, "Owner's private task")
    other = login_as("other_user")
    other_task = create_task(other, api_url, "Other user's task")
    url = f"{api_url}/tasks/{owner_task['id']}"
    for method in ("GET", "PATCH", "DELETE"):
        response = other.request(method, url, json={"title": "Stolen task"}, timeout=3)
        missing = other.request(method, f"{api_url}/tasks/999999", json={"title": "X"}, timeout=3)
        assert response.status_code == missing.status_code == 404
        assert response.json() == missing.json() == {"error": "Task not found"}
    assert other.get(f"{api_url}/tasks", timeout=3).json() == [other_task]
    assert http.get(f"{api_url}/tasks", timeout=3).json() == [owner_task]
    with app.app_context():
        rows = get_db().execute(
            "SELECT u.username, t.title FROM users u JOIN tasks t ON t.owner_id = u.id ORDER BY t.id"
        ).fetchall()
        assert [tuple(row) for row in rows] == [
            ("qa_owner", owner_task["title"]), ("other_user", other_task["title"])]


@pytest.mark.parametrize("title", ["A", "A" * 100, "Проверить звонок ☎", "  Keep spaces  ",
                                  "'); DROP TABLE tasks; --"])
def test_valid_titles_round_trip(api_url, http, title):
    task = create_task(http, api_url, title)
    assert task["title"] == title
    assert http.get(f"{api_url}/tasks/{task['id']}", timeout=3).json() == task
    assert http.get(f"{api_url}/tasks", timeout=3).json() == [task]


@pytest.mark.parametrize("title", ["A" * 101, " \t\n", None, True, [], {}, "\u0000task"])
def test_invalid_titles_leave_database_unchanged(api_url, http, app, title):
    task = create_task(http, api_url)
    response = http.post(f"{api_url}/tasks", json={"title": title}, timeout=3)
    assert response.status_code == 400
    assert "error" in response.json()
    assert http.get(f"{api_url}/tasks", timeout=3).json() == [task]
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1


@pytest.mark.parametrize("patch", [
    {}, {"owner_id": 2}, {"title": ""}, {"title": "X" * 101}, {"title": "\u0000task"},
    {"title": "Would partially update", "completed": 1},
    {"title": "Would partially update", "completed": "true"},
    {"title": "Would partially update", "completed": None},
])
def test_rejected_patch_is_atomic(api_url, http, app, patch):
    task = create_task(http, api_url)
    url = f"{api_url}/tasks/{task['id']}"
    response = http.patch(url, json=patch, timeout=3)
    assert response.status_code == 400
    assert http.get(url, timeout=3).json() == task
    with app.app_context():
        saved = get_db().execute("SELECT title, completed FROM tasks WHERE id = ?", (task["id"],)).fetchone()
        assert tuple(saved) == (task["title"], 0)


def test_filter_and_pagination_apply_to_current_user(api_url, http, login_as):
    tasks = [create_task(http, api_url, f"Task {i}") for i in range(4)]
    for index in (1, 3):
        response = http.patch(f"{api_url}/tasks/{tasks[index]['id']}", json={"completed": True}, timeout=3)
        assert response.status_code == 200
        tasks[index]["completed"] = True
    create_task(login_as("another_owner"), api_url, "Not in the owner's page")
    for query, expected in [
        ("", tasks), ("?limit=2&offset=1", tasks[1:3]),
        ("?completed=true", [tasks[1], tasks[3]]),
        ("?completed=false", [tasks[0], tasks[2]]),
        ("?completed=true&limit=1&offset=1", [tasks[3]]), ("?offset=100", []),
    ]:
        response = http.get(f"{api_url}/tasks{query}", timeout=3)
        assert response.status_code == 200
        assert response.json() == expected


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "limit=-1", "limit=1.5",
    "offset=-1", "offset=2147483648", "completed=1", "completed=True",
    "limit=1&limit=2", "owner_id=2", "offset=abc"])
def test_invalid_query_rejected_without_mutation(api_url, http, query):
    task = create_task(http, api_url)
    response = http.get(f"{api_url}/tasks?{query}", timeout=3)
    assert response.status_code == 400
    assert "error" in response.json()
    assert http.get(f"{api_url}/tasks", timeout=3).json() == [task]


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize("task_id", [0, 999999, 9223372036854775808])
def test_unknown_ids_return_404(api_url, http, method, task_id):
    response = http.request(method, f"{api_url}/tasks/{task_id}", json={"completed": True}, timeout=3)
    assert response.status_code == 404
    assert response.json() == {"error": "Task not found"}


def test_cannot_choose_task_owner(api_url, http):
    response = http.post(f"{api_url}/tasks", json={"title": "Task", "owner_id": 2}, timeout=3)
    assert response.status_code == 400
    assert http.get(f"{api_url}/tasks", timeout=3).json() == []
