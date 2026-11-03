"""Run the versioned Postman collection against an isolated local Task API."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Thread

from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from task_api import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 10:
        parser.error("--iterations must be between 1 and 10")
    node = shutil.which("node")
    newman = ROOT / "node_modules" / "newman" / "bin" / "newman.js"
    if not node or not newman.is_file():
        parser.error("Install Node.js and run npm ci in the project directory first")

    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="task-api-postman-") as temp:
        app = create_app({"DATABASE": str(Path(temp) / "tasks.sqlite3"), "TESTING": True})
        # Binding before starting the thread avoids guessed ports and startup sleeps.
        server = make_server("127.0.0.1", 0, app)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        try:
            command = [node, str(newman), "run", str(ROOT / "postman" / "Task_API.postman_collection.json"),
                "--environment", str(ROOT / "postman" / "local.postman_environment.json"),
                "--env-var", f"base_url=http://127.0.0.1:{server.server_port}",
                "--iteration-count", str(args.iterations), "--timeout-request", "5000",
                "--timeout", "90000", "--ignore-redirects", "--bail",
                "--reporters", "cli,junit", "--reporter-junit-export", str(reports / "postman.xml")]
            # Keep even loopback traffic independent of a developer's proxy setup.
            env = dict(os.environ)
            env["NO_PROXY"] = "127.0.0.1,localhost"
            env["no_proxy"] = "127.0.0.1,localhost"
            result = subprocess.run(command, cwd=ROOT, env=env, timeout=120, check=False)
            return result.returncode
        except subprocess.TimeoutExpired:
            print("Newman exceeded its execution limit", file=sys.stderr)
            return 1
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            if thread.is_alive():
                raise RuntimeError("The temporary HTTP server did not stop")


if __name__ == "__main__":
    sys.exit(main())
