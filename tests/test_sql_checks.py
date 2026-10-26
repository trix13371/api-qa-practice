"""Execute the portfolio SQL against known HTTP-created data."""
from pathlib import Path

from storage import get_db


def test_documented_sql_checks(api_url, http, login_as, app):
    response = http.post(f"{api_url}/tasks", json={"title": "SQL verification"}, timeout=3)
    assert response.status_code == 201
    task = response.json()
    response = http.patch(f"{api_url}/tasks/{task['id']}", json={"completed": True}, timeout=3)
    assert response.status_code == 200
    login_as("user_without_tasks")
    sql = (Path(__file__).resolve().parents[1] / "docs" / "sql-checks.sql").read_text(encoding="utf-8")
    with app.app_context():
        results = [get_db().execute(statement).fetchall()
                   for statement in sql.split(";") if statement.strip()]
        assert len(results) == 4
        assert [tuple(row) for row in results[0]] == [(task["id"], "qa_owner", task["title"], 1)]
        assert [tuple(row) for row in results[1]] == [
            ("qa_owner", 1, 1), ("user_without_tasks", 0, 0)]
        assert results[2] == results[3] == []
