"""HTTP error format, diagnostics and persistence across an actual server restart."""
import logging
import uuid

import pytest

from conftest import running_server
from task_api import create_app


@pytest.mark.parametrize("body,content_type", [
    ('{"title":', "application/json"), ('[]', "application/json"),
    ('null', "application/json"), ('"text"', "application/json"),
    ('{"title":"Task"}', "text/plain"),
])
def test_invalid_body_rejected(api_url, http, body, content_type):
    response = http.post(f"{api_url}/tasks", data=body, headers={"Content-Type": content_type}, timeout=3)
    assert response.status_code == 400
    assert response.json() == {"error": "JSON object required"}
    assert http.get(f"{api_url}/tasks", timeout=3).json() == []


def test_oversized_body_rejected(api_url, http):
    response = http.post(f"{api_url}/tasks", json={"title": "X" * (65 * 1024)}, timeout=3)
    assert response.status_code == 413
    assert "error" in response.json()
    assert http.get(f"{api_url}/tasks", timeout=3).json() == []


@pytest.mark.parametrize("method,path,status", [
    ("GET", "/unknown", 404), ("PUT", "/tasks", 405),
])
def test_routing_errors_use_json(api_url, http, method, path, status):
    response = http.request(method, api_url + path, timeout=3)
    assert response.status_code == status
    assert response.headers["Content-Type"].startswith("application/json")
    assert "error" in response.json()
    if status == 405:
        allowed_methods = {item.strip() for item in response.headers["Allow"].split(",")}
        assert {"GET", "POST"} <= allowed_methods
        assert "PUT" not in allowed_methods


def test_request_id_links_response_to_safe_log(api_url, http, caplog):
    caplog.clear()
    with caplog.at_level(logging.INFO):
        response = http.post(f"{api_url}/tasks", json={"title": "Private title not for logs"}, timeout=3)
    assert response.status_code == 201
    request_id = response.headers["X-Request-ID"]
    assert str(uuid.UUID(request_id)) == request_id
    assert response.headers["Cache-Control"] == "no-store"
    assert f"request_id={request_id} method=POST path=/tasks status=201 duration_ms=" in caplog.text
    assert "Private title not for logs" not in caplog.text
    assert http.headers["Authorization"] not in caplog.text


def test_health_is_available_without_authentication(api_url, anonymous_http):
    response = anonymous_http.get(f"{api_url}/health", timeout=3)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_restart_preserves_users_sessions_and_tasks(tmp_path, anonymous_http):
    config = {"DATABASE": str(tmp_path / "persistent.sqlite3"), "TESTING": True}
    with running_server(create_app(config)) as url:
        response = anonymous_http.post(f"{url}/users", json={
            "username": "persistent_user", "password": "password123"}, timeout=3)
        assert response.status_code == 201
        login = anonymous_http.post(f"{url}/auth/login", json={
            "username": "persistent_user", "password": "password123"}, timeout=3)
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        created = anonymous_http.post(f"{url}/tasks", json={"title": "Survive restart"}, headers=headers, timeout=3)
        assert created.status_code == 201
        task = created.json()
    # A new application and HTTP server open the SAME file, not an in-memory mock.
    with running_server(create_app(config)) as url:
        response = anonymous_http.get(f"{url}/tasks", headers=headers, timeout=3)
        assert response.status_code == 200
        assert response.json() == [task]
        login = anonymous_http.post(f"{url}/auth/login", json={
            "username": "persistent_user", "password": "password123"}, timeout=3)
        assert login.status_code == 200
        created = anonymous_http.post(f"{url}/tasks", json={"title": "After restart"}, headers=headers, timeout=3)
        assert created.status_code == 201
        assert created.json()["id"] > task["id"]
