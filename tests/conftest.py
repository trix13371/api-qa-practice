from threading import Thread

import pytest
from requests import Session
from werkzeug.serving import make_server

from task_api import create_app


@pytest.fixture
def api_url():
    """Give each test an empty API on a free local port."""
    server = make_server("127.0.0.1", 0, create_app())
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
def http():
    """Keep local requests independent of machine proxy settings."""
    with Session() as session:
        session.trust_env = False
        yield session
