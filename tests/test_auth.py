"""Registration, credentials and the lifetime of bearer sessions."""
import hashlib

import pytest
from werkzeug.security import check_password_hash

from storage import get_db


@pytest.mark.parametrize("username,password,status", [
    ("ab", "password123", 400), ("abc", "password123", 201),
    ("u" * 32, "password123", 201), ("u" * 33, "password123", 400),
    ("qa user", "password123", 400), ("пользователь", "password123", 400),
    (123, "password123", 400), (None, "password123", 400),
    ("qa_user", "p" * 7, 400), ("qa_user", "p" * 8, 201),
    ("qa_user", "p" * 128, 201), ("qa_user", "p" * 129, 400),
    ("qa_user", " " * 8, 400), ("qa_user", 12345678, 400),
])
def test_registration_boundaries(api_url, anonymous_http, app, username, password, status):
    response = anonymous_http.post(f"{api_url}/users", json={
        "username": username, "password": password}, timeout=3)
    assert response.status_code == status, response.text
    with app.app_context():
        users = get_db().execute("SELECT * FROM users").fetchall()
    if status == 201:
        assert response.json() == {"id": users[0]["id"], "username": username}
        assert len(users) == 1
        assert users[0]["password_hash"] != password
        assert check_password_hash(users[0]["password_hash"], password)
    else:
        assert "error" in response.json()
        assert len(users) == 0


def test_duplicate_registration_keeps_original_password(api_url, anonymous_http, http):
    duplicate = anonymous_http.post(f"{api_url}/users", json={
        "username": "qa_owner", "password": "replacement123"}, timeout=3)
    assert duplicate.status_code == 409
    for password, status in [("replacement123", 401), ("Training_password_123!", 200)]:
        login = anonymous_http.post(f"{api_url}/auth/login", json={
            "username": "qa_owner", "password": password}, timeout=3)
        assert login.status_code == status


def test_unknown_user_and_wrong_password_have_same_response(api_url, anonymous_http, http):
    responses = [anonymous_http.post(f"{api_url}/auth/login", json={
        "username": username, "password": "wrong_password"}, timeout=3)
        for username in ("qa_owner", "unknown_user")]
    assert [response.status_code for response in responses] == [401, 401]
    assert responses[0].json() == responses[1].json() == {"error": "Invalid credentials"}


@pytest.mark.parametrize("authorization", [None, "Bearer", "Bearer invalid_token", "Basic abc", "Bearer a b"])
@pytest.mark.parametrize("method,path", [
    ("GET", "/tasks"), ("POST", "/tasks"), ("GET", "/tasks/1"),
    ("PATCH", "/tasks/1"), ("DELETE", "/tasks/1"), ("POST", "/auth/logout"),
])
def test_invalid_authorization_rejected(api_url, anonymous_http, authorization, method, path):
    headers = {} if authorization is None else {"Authorization": authorization}
    response = anonymous_http.request(method, api_url + path, headers=headers,
                                      json={"title": "Unauthorized task"}, timeout=3)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json() == {"error": "Authentication required"}


def test_expired_token_rejected(api_url, http, app):
    # Arrange expiry directly in the DB, avoiding an hour-long wait and flaky sleeps.
    token = http.headers["Authorization"].split()[1]
    with app.app_context():
        db = get_db()
        session = db.execute("SELECT * FROM sessions").fetchone()
        assert session["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
        assert session["token_hash"] != token
        db.execute("UPDATE sessions SET expires_at = 0")
        db.commit()
    assert http.get(f"{api_url}/tasks", timeout=3).status_code == 401


def test_logout_revokes_only_current_session(api_url, http, anonymous_http):
    response = anonymous_http.post(f"{api_url}/auth/login", json={
        "username": "qa_owner", "password": "Training_password_123!"}, timeout=3)
    assert response.status_code == 200
    credentials = response.json()
    assert credentials["token_type"] == "Bearer"
    assert credentials["expires_in"] == 3600
    other_headers = {"Authorization": f"Bearer {credentials['access_token']}"}
    assert other_headers["Authorization"] != http.headers["Authorization"]
    logout = http.post(f"{api_url}/auth/logout", timeout=3)
    assert logout.status_code == 204
    assert logout.content == b""
    assert http.get(f"{api_url}/tasks", timeout=3).status_code == 401
    assert http.post(f"{api_url}/auth/logout", timeout=3).status_code == 401
    assert anonymous_http.get(f"{api_url}/tasks", headers=other_headers, timeout=3).status_code == 200


@pytest.mark.parametrize("path", ["/users", "/auth/login"])
@pytest.mark.parametrize("payload", [{}, {"username": "qa"},
    {"username": "qa_user", "password": "password123", "role": "admin"}])
def test_credentials_require_exact_fields(api_url, anonymous_http, path, payload):
    response = anonymous_http.post(api_url + path, json=payload, timeout=3)
    assert response.status_code == 400
