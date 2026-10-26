from contextlib import ExitStack, contextmanager
from threading import Thread

import pytest
from requests import Session
from werkzeug.serving import make_server

from task_api import create_app


@contextmanager
def running_server(app):
    """Use real HTTP; bind first so no guessed ports or startup sleeps are needed."""
    server = make_server("127.0.0.1", 0, app)
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()

    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()
        assert not thread.is_alive(), "The test server did not stop"


@pytest.fixture
def app(tmp_path):
    return create_app({"DATABASE": str(tmp_path / "tasks.sqlite3"), "TESTING": True})


@pytest.fixture
def api_url(app):
    """Isolate both database and server for each test."""
    with running_server(app) as url:
        yield url


@pytest.fixture
def anonymous_http():
    """Keep local requests independent of machine proxy settings."""
    with Session() as session:
        session.trust_env = False
        yield session


@pytest.fixture
def login_as(api_url, anonymous_http):
    """Register independent users and close all their HTTP sessions afterwards."""
    with ExitStack() as stack:
        def create_user(username, password="Training_password_123!"):
            response = anonymous_http.post(f"{api_url}/users", json={
                "username": username, "password": password}, timeout=3)
            assert response.status_code == 201, response.text
            response = anonymous_http.post(f"{api_url}/auth/login", json={
                "username": username, "password": password}, timeout=3)
            assert response.status_code == 200, response.text
            session = stack.enter_context(Session())
            session.trust_env = False
            session.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
            return session
        yield create_user


@pytest.fixture
def http(login_as):
    return login_as("qa_owner")
