# Task API — тестирование сервиса личных задач

[English](docs/README.en.md) · [GitHub Actions](https://github.com/trix13371/api-qa-practice/actions)

[![API tests](https://github.com/trix13371/api-qa-practice/actions/workflows/tests.yml/badge.svg)](https://github.com/trix13371/api-qa-practice/actions/workflows/tests.yml)

Учебный QA-проект с полным жизненным циклом задачи: регистрация → вход → создание → изменение → фильтрация → удаление. Python, pytest, requests, Flask и SQLite.

Акцент на проверках бизнес-правил и данных: чужая задача недоступна, отклонённое изменение не записывается частично, данные сохраняются после перезапуска. Автотесты работают через настоящие HTTP-запросы. Для нескольких сценариев результат дополнительно проверяется SQL-запросом к БД.

## Что смотреть работодателю

| Навык | Доказательство в проекте |
| --- | --- |
| Анализ требований и тест-дизайн | [Контракт](docs/api-contract.md), [тест-план с рисками и связями с тестами](docs/test-plan.md) |
| API и Python | [Жизненный цикл, границы, негативные сценарии](tests/test_workflows.py) |
| Авторизация и разграничение доступа | [Сессии](tests/test_auth.py), проверка двух владельцев в test_workflows.py |
| SQL и целостность данных | [Схема БД](schema.sql), [контрольные SQL-запросы](docs/sql-checks.sql), SQL assertions в тестах |
| Диагностика и регрессия | [Обнаруженный и исправленный дефект](docs/bug-report-001.md), корреляция ответа с логом по X-Request-ID |
| Воспроизводимость и CI | [Фикстуры](tests/conftest.py), [workflow](.github/workflows/tests.yml), JUnit-отчёт |
| Ручное тестирование API | [Подтверждённые проверки в Postman](docs/manual-checks.md) |

[Результаты локальной проверки](docs/test-results.md): **114 passed**. Параметризация входит в это число; это не 114 независимых бизнес-сценариев. Результат CI для публикуемой версии проверяется отдельно от локального прогона.

## Быстрый запуск

Python 3.14. Windows, из папки проекта:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -v --junitxml=reports/junit.xml
```

Linux/macOS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -v --junitxml=reports/junit.xml
```

Сервер запускается автоматически. Каждый тест получает временную БД и свободный локальный порт; пользовательские данные не затрагиваются. JUnit XML создаётся в reports/ и не попадает в Git.

## Ручная практика

Запуск сервиса:

```powershell
.\.venv\Scripts\python.exe -m flask --app task_api run --host 127.0.0.1 --port 8000
```

В другом терминале PowerShell:

```powershell
$apiBase = 'http://127.0.0.1:8000'
$credentials = '{"username":"qa_demo","password":"Training_password_123!"}'
Invoke-RestMethod "$apiBase/users" -Method Post -ContentType 'application/json' -Body $credentials
$login = Invoke-RestMethod "$apiBase/auth/login" -Method Post -ContentType 'application/json' -Body $credentials
$authHeaders = @{ Authorization = "Bearer $($login.access_token)" }
$task = Invoke-RestMethod "$apiBase/tasks" -Method Post -Headers $authHeaders -ContentType 'application/json' -Body '{"title":"Check task lifecycle"}'
Invoke-RestMethod "$apiBase/tasks/$($task.id)" -Method Patch -Headers $authHeaders -ContentType 'application/json' -Body '{"completed":true}'
Invoke-RestMethod "$apiBase/tasks?completed=true" -Headers $authHeaders
Invoke-RestMethod "$apiBase/tasks/$($task.id)" -Method Delete -Headers $authHeaders
```

При повторе регистрации того же имени ожидается 409: пропусти регистрацию и войди либо выбери новое имя. Остановка сервера: Ctrl+C. База по умолчанию — instance/tasks.sqlite3; при перезапуске сохраняется. Другой путь задаётся переменной TASK_API_DATABASE. Пароли и токены из примера предназначены только для локальной практики.

## Как устроен проект

- application.py - маршруты, валидация и права владельца.
- storage.py и schema.sql - соединения и хранение в SQLite.
- task_api.py - точка входа Flask.
- tests/ - HTTP-проверки и подготовка тестовых ресурсов.
- [Разбор тестов](docs/walkthrough.md) - порядок изучения и вопросы для самопроверки.

Это расширение первоначального проекта с четырьмя проверками. В новой версии /tasks требует Bearer-токен; неизвестные поля отклоняются. База создаётся автоматически для новой установки; миграции произвольных старых схем не предусмотрены.

## Границы проекта

Это учебная работа, не коммерческий опыт. Сервис предназначен для локального запуска, используется сервер разработки Flask. Нагрузочное тестирование, конкурентные обновления, восстановление пароля и полноценный аудит безопасности не проводились. SQLite здесь не выдаётся за PostgreSQL. Подробнее о непокрытых рисках - в тест-плане.
