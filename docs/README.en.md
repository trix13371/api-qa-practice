# Task API — API test automation practice

[Русский](../README.md)

[![API tests](https://github.com/trix13371/api-qa-practice/actions/workflows/tests.yml/badge.svg)](https://github.com/trix13371/api-qa-practice/actions/workflows/tests.yml)

A small in-memory Flask service and Python tests using pytest and requests. Tests send real HTTP requests to a local server, not a mock. No external account, website, or Docker is required.

This is a starter learning project, not commercial experience. Only create, list, and retrieve endpoints are implemented.

## Coverage

Two test functions produce **four test cases**:

1. Create a task: verify HTTP 201, JSON, positive integer ID, title and completion flag; read it back through list and detail endpoints.
2. Reject an empty title, a numeric title, and a missing title: verify HTTP 400, the error message, and that existing tasks remain unchanged.

Each case gets a new empty server on a free local port, with automatic cleanup. Requests have timeouts. Tests do not rely on earlier executions.

## Run on Windows

Install Python 3.14 and open a terminal in the project directory. Environment activation is unnecessary.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -v
```

Expected result: `4 passed`. Tests start the server automatically.

## Run on Linux/macOS

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -v
```

Verified locally on Windows and on Linux in GitHub Actions: [successful CI run](https://github.com/trix13371/api-qa-practice/actions/runs/34808870164).

## Manual API practice

Start the server in one Windows terminal:

```powershell
.\.venv\Scripts\python.exe -m flask --app task_api run --host 127.0.0.1 --port 8000
```

Send requests from another PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/tasks -Method Post -ContentType 'application/json' -Body '{"title":"Learn API"}'
Invoke-RestMethod http://127.0.0.1:8000/tasks
```

Stop with `Ctrl+C`. Restarting clears the data. The service is for local practice only.

## Project files

- [Test cases](../tests/test_tasks.py)
- [Server and client fixtures](../tests/conftest.py)
- [Application](../task_api.py)
- [API contract and limitations](api-contract.md)
- [Russian beginner walkthrough](walkthrough.md)
- [Verification results](test-results.md)
- [GitHub Actions workflow](../.github/workflows/tests.yml)

## Reports and CI

```powershell
.\.venv\Scripts\python.exe -m pytest -v --junitxml=reports/junit.xml
```

Generated `reports/` is ignored by Git. The workflow runs on push and pull requests and uploads XML as `api-test-results`. See the [Actions tab](https://github.com/trix13371/api-qa-practice/actions) for run results.

## Next steps

Add unknown-ID, whitespace-only title and malformed-JSON tests. Implement update and delete endpoints later. These are outside the current scope.
