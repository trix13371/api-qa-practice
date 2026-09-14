# Task API — учебный проект по автоматизации тестирования

[English](docs/README.en.md)

[![API tests](https://github.com/trix13371/api-qa-practice/actions/workflows/tests.yml/badge.svg)](https://github.com/trix13371/api-qa-practice/actions/workflows/tests.yml)

Небольшой API управления задачами и автотесты на Python: pytest + requests. Тесты отправляют настоящие HTTP-запросы локальному серверу Flask. Внешний сайт, аккаунт и Docker не нужны.

Это стартовый учебный проект, а не коммерческий опыт. Реализованы создание, получение списка и получение задачи по ID. Данные хранятся только в памяти.

## Что проверяется

Две тестовые функции дают **четыре отдельных запуска**:

1. Создание задачи: статус 201, JSON, ID, название, признак выполнения; затем чтение сохранённой задачи через список и по ID.
2. Отклонение неверного названия: пустая строка, число и отсутствие поля. Для каждого варианта проверяются статус 400, сообщение об ошибке и сохранность существующих задач.

Перед каждым запуском создаётся отдельный пустой сервер на свободном порту, после — останавливается. Запросы имеют тайм-аут. Тесты не зависят от данных предыдущего запуска.

## Запуск в Windows

Нужен Python 3.14. Открой терминал в папке проекта. Активация виртуального окружения не требуется.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -v
```

Ожидаемый итог: `4 passed`. Сервер для тестов запускается автоматически.

## Запуск в Linux/macOS

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -v
```

Проверено локально в Windows и в GitHub Actions на Linux: [успешный запуск CI](https://github.com/trix13371/api-qa-practice/actions/runs/34808870164).

## Ручные запросы

В первом терминале:

```powershell
.\.venv\Scripts\python.exe -m flask --app task_api run --host 127.0.0.1 --port 8000
```

Во втором терминале PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/tasks -Method Post -ContentType 'application/json' -Body '{"title":"Learn API"}'
Invoke-RestMethod http://127.0.0.1:8000/tasks
```

Остановка: `Ctrl+C`. После перезапуска задачи исчезнут. Сервер предназначен только для локальной практики.

## Файлы

- [tests/test_tasks.py](tests/test_tasks.py) — проверки.
- [tests/conftest.py](tests/conftest.py) — подготовка сервера и HTTP-клиента.
- [task_api.py](task_api.py) — учебный сервис.
- [Требования к API](docs/api-contract.md) — ожидаемое поведение и ограничения.
- [Разбор кода](docs/walkthrough.md) — с чего начать изучение.
- [Результаты проверки](docs/test-results.md) — локальный прогон и обнаружение намеренной ошибки.
- [GitHub Actions](.github/workflows/tests.yml) — запуск при push и pull request.

## Отчёт и CI

```powershell
.\.venv\Scripts\python.exe -m pytest -v --junitxml=reports/junit.xml
```

XML-отчёт создаётся в `reports/`; папка не включается в Git. Workflow запускает тесты при push и pull request и прикладывает XML как артефакт `api-test-results`. Результаты доступны на вкладке [Actions](https://github.com/trix13371/api-qa-practice/actions).

## Дальнейшее развитие

Добавить проверки неизвестного ID, пробельного названия и некорректного JSON. Затем — изменение и удаление задач. Сейчас эти проверки и методы изменения/удаления не реализованы.
