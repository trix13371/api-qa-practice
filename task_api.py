"""A small in-memory API for practising HTTP tests."""

from flask import Flask, jsonify, request


def create_app():
    app = Flask(__name__)
    tasks = {}
    next_id = 1

    @app.get("/tasks")
    def list_tasks():
        return jsonify(list(tasks.values()))

    @app.post("/tasks")
    def create_task():
        nonlocal next_id
        payload = request.get_json(silent=True)

        if not isinstance(payload, dict):
            return jsonify(error="JSON object required"), 400

        title = payload.get("title")
        if not isinstance(title, str) or not title.strip():
            return jsonify(error="title must be a non-empty string"), 400

        task = {"id": next_id, "title": title, "completed": False}
        tasks[next_id] = task
        next_id += 1
        return jsonify(task), 201

    @app.get("/tasks/<int:task_id>")
    def get_task(task_id):
        if task_id not in tasks:
            return jsonify(error="Task not found"), 404
        return jsonify(tasks[task_id])

    return app
