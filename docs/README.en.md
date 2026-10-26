# Task API — QA portfolio project

[Русский](../README.md)

A local task service with registration, bearer sessions, owner-isolated CRUD, filtering, pagination and persistent SQLite storage. Tests use pytest and requests over real HTTP, not Flask's test client or a mocked API.

## Evidence

- [Contract](api-contract.md): explicit validation, access and state rules.
- [Risk-based test plan](test-plan.md): requirements mapped to executable scenarios.
- [Tests](../tests): boundaries, negative cases, full task lifecycle, two-user isolation, atomic updates, session expiry/logout and persistence after a server restart.
- [SQL checks](sql-checks.sql): joins, aggregation and integrity diagnostics.
- [Defect report](bug-report-001.md): an observed validation/storage mismatch, fix and regression.
- [Manual API checks](manual-checks.md): recorded Postman results, separate from automated test coverage.
- [Verification](test-results.md): 114 cases passed locally on Windows, including parametrization. This is not 114 distinct business workflows.

## Run

Python 3.14, Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -v --junitxml=reports/junit.xml
```

Linux/macOS: use python3 and .venv/bin/python. Tests create an isolated temporary database and automatically manage a local server on a free port.

Manual server:

```powershell
.\.venv\Scripts\python.exe -m flask --app task_api run --host 127.0.0.1 --port 8000
```

Register via POST /users, log in via POST /auth/login, then use Authorization: Bearer <access_token> on /tasks. See the main README for a complete PowerShell example. The default database is instance/tasks.sqlite3; TASK_API_DATABASE overrides the path. Restarting preserves data.

Version 2 changes the old API: tasks now require authentication and unknown fields are rejected. Schema migrations for existing arbitrary databases are not included.

## CI and scope

[Workflow](../.github/workflows/tests.yml) runs pytest on pushes and pull requests, and uploads JUnit XML. The expanded version has been verified locally; its GitHub Actions result must be checked after publishing.

This is a learning project, not commercial work or a production-ready service. SQLite is not PostgreSQL. Load testing, concurrent updates, password recovery and a comprehensive security audit are outside the verified scope. [Beginner walkthrough, Russian](walkthrough.md).
