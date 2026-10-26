"""Training API with SQLite, bearer sessions and owner-isolated task CRUD."""
from functools import wraps
import hashlib
import logging
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from storage import get_db, init_storage


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("TASK_API_DATABASE", str(Path(app.instance_path) / "tasks.sqlite3")),
        TOKEN_TTL_SECONDS=3600, MAX_CONTENT_LENGTH=64 * 1024,
    )
    if config:
        app.config.update(config)
    init_storage(app)

    @app.before_request
    def start_request():
        g.request_id = str(uuid.uuid4())
        g.started_at = time.monotonic()

    @app.after_request
    def record_response(response):
        response.headers["X-Request-ID"] = g.request_id
        response.headers["Cache-Control"] = "no-store"
        app.logger.info("request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                        g.request_id, request.method, request.path, response.status_code,
                        (time.monotonic() - g.started_at) * 1000)
        return response

    def fail(message, status=400):
        response = jsonify(error=message)
        response.status_code = status
        if status == 401:
            response.headers["WWW-Authenticate"] = "Bearer"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        # Retain protocol headers, e.g. Allow on 405, while replacing HTML with JSON.
        response = error.get_response()
        response.set_data(jsonify(error=error.name).get_data())
        response.content_type = "application/json"
        return response

    def payload():
        if not request.is_json:
            return None
        value = request.get_json(silent=True)
        return value if isinstance(value, dict) else None

    def protected(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            parts = request.headers.get("Authorization", "").split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return fail("Authentication required", 401)
            digest = hashlib.sha256(parts[1].encode()).hexdigest()
            session = get_db().execute(
                "SELECT user_id FROM sessions WHERE token_hash = ? AND expires_at > ?",
                (digest, time.time()),
            ).fetchone()
            if session is None:
                return fail("Authentication required", 401)
            g.user_id, g.token_hash = session["user_id"], digest
            return function(*args, **kwargs)
        return wrapper

    def valid_title(value):
        # SQLite length(TEXT) stops at U+0000. Reject NUL before the DB constraint.
        return (isinstance(value, str) and "\x00" not in value
                and bool(value.strip()) and 1 <= len(value) <= 100)

    def task_json(row):
        return {"id": row["id"], "title": row["title"], "completed": bool(row["completed"])}

    def owned_task(task_id):
        if task_id > 9223372036854775807:
            return None
        return get_db().execute("SELECT * FROM tasks WHERE id = ? AND owner_id = ?",
                                (task_id, g.user_id)).fetchone()

    @app.get("/health")
    def health():
        get_db().execute("SELECT 1").fetchone()
        return jsonify(status="ok")

    @app.post("/users")
    def register():
        data = payload()
        if data is None:
            return fail("JSON object required")
        if set(data) != {"username", "password"}:
            return fail("username and password required; unknown fields are not allowed")
        username, password = data["username"], data["password"]
        if not isinstance(username, str) or re.fullmatch(r"[A-Za-z0-9_]{3,32}", username) is None:
            return fail("username must contain 3-32 ASCII letters, digits or underscores")
        if not isinstance(password, str) or not password.strip() or not 8 <= len(password) <= 128:
            return fail("password must contain 8-128 characters and not be blank")
        try:
            db = get_db()
            cursor = db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                                (username, generate_password_hash(password)))
            db.commit()
        except sqlite3.IntegrityError:
            db.rollback()
            return fail("Username already registered", 409)
        return jsonify(id=cursor.lastrowid, username=username), 201

    @app.post("/auth/login")
    def login():
        data = payload()
        if data is None:
            return fail("JSON object required")
        if set(data) != {"username", "password"}:
            return fail("username and password required; unknown fields are not allowed")
        if not isinstance(data["username"], str) or not isinstance(data["password"], str):
            return fail("Credentials must be strings")
        row = get_db().execute("SELECT * FROM users WHERE username = ?", (data["username"],)).fetchone()
        if row is None or not check_password_hash(row["password_hash"], data["password"]):
            return fail("Invalid credentials", 401)
        token = secrets.token_urlsafe(32)
        get_db().execute("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                         (hashlib.sha256(token.encode()).hexdigest(), row["id"],
                          time.time() + app.config["TOKEN_TTL_SECONDS"]))
        get_db().commit()
        return jsonify(access_token=token, token_type="Bearer", expires_in=app.config["TOKEN_TTL_SECONDS"])

    @app.post("/auth/logout")
    @protected
    def logout():
        get_db().execute("DELETE FROM sessions WHERE token_hash = ?", (g.token_hash,))
        get_db().commit()
        return "", 204

    @app.get("/tasks")
    @protected
    def list_tasks():
        if set(request.args) - {"completed", "limit", "offset"} or any(
                len(request.args.getlist(key)) != 1 for key in request.args):
            return fail("Unknown or repeated query parameter")
        completed = request.args.get("completed")
        if completed is not None and completed not in ("true", "false"):
            return fail("completed must be true or false")
        raw_limit, raw_offset = request.args.get("limit", "100"), request.args.get("offset", "0")
        if re.fullmatch(r"[0-9]{1,3}", raw_limit) is None or re.fullmatch(r"[0-9]{1,10}", raw_offset) is None:
            return fail("Invalid pagination")
        limit, offset = int(raw_limit), int(raw_offset)
        if not 1 <= limit <= 100 or offset > 2147483647:
            return fail("Invalid pagination")
        sql, args = "SELECT * FROM tasks WHERE owner_id = ?", [g.user_id]
        if completed is not None:
            sql += " AND completed = ?"
            args.append(int(completed == "true"))
        rows = get_db().execute(sql + " ORDER BY id LIMIT ? OFFSET ?", args + [limit, offset]).fetchall()
        return jsonify([task_json(row) for row in rows])

    @app.post("/tasks")
    @protected
    def create_task():
        data = payload()
        if data is None:
            return fail("JSON object required")
        if set(data) - {"title"}:
            return fail("Unknown fields are not allowed")
        if not valid_title(data.get("title")):
            return fail("title must be a non-blank string of 1-100 characters")
        db = get_db()
        cursor = db.execute("INSERT INTO tasks (owner_id, title, completed) VALUES (?, ?, 0)",
                            (g.user_id, data["title"]))
        db.commit()
        return jsonify(task_json(owned_task(cursor.lastrowid))), 201

    @app.get("/tasks/<int:task_id>")
    @protected
    def get_task(task_id):
        row = owned_task(task_id)
        return fail("Task not found", 404) if row is None else jsonify(task_json(row))

    @app.patch("/tasks/<int:task_id>")
    @protected
    def update_task(task_id):
        row = owned_task(task_id)
        if row is None:
            return fail("Task not found", 404)
        data = payload()
        if data is None:
            return fail("JSON object required")
        if not data or set(data) - {"title", "completed"}:
            return fail("Provide title or completed; unknown fields are not allowed")
        if "title" in data and not valid_title(data["title"]):
            return fail("title must be a non-blank string of 1-100 characters")
        if "completed" in data and type(data["completed"]) is not bool:
            return fail("completed must be a boolean")
        get_db().execute("UPDATE tasks SET title = ?, completed = ? WHERE id = ? AND owner_id = ?",
                         (data.get("title", row["title"]), int(data.get("completed", bool(row["completed"]))),
                          task_id, g.user_id))
        get_db().commit()
        return jsonify(task_json(owned_task(task_id)))

    @app.delete("/tasks/<int:task_id>")
    @protected
    def delete_task(task_id):
        if owned_task(task_id) is None:
            return fail("Task not found", 404)
        get_db().execute("DELETE FROM tasks WHERE id = ? AND owner_id = ?", (task_id, g.user_id))
        get_db().commit()
        return "", 204

    app.logger.setLevel(logging.INFO)
    return app
