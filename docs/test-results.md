# Проверка проекта / Project verification

## Окружение / Environment

Windows, Python 3.14.7, Flask 3.1.3, pytest 9.1.1, requests 2.34.2. Локальный HTTP-сервер / local HTTP server.

## Основной прогон / Main suite

```powershell
.\.venv\Scripts\python.exe -m pytest -v --junitxml=reports/junit.xml
```

| Case | Result |
| --- | --- |
| test_create_task_and_read_it_back | PASSED |
| test_invalid_task_does_not_change_saved_tasks[empty-title] | PASSED |
| test_invalid_task_does_not_change_saved_tasks[numeric-title] | PASSED |
| test_invalid_task_does_not_change_saved_tasks[missing-title] | PASSED |

Итог: **4 passed**. Две тестовые функции, четыре запуска с учётом параметризации.

Result: **4 passed**. Two test functions, four executions including parametrization.

## Намеренная ошибка / Deliberate regression check

Временно в сервисе название создаваемой задачи заменено на `Wrong title`. Положительный тест завершился с `1 failed`: ожидалось `Learn API`, получено `Wrong title`. Сервер продолжал возвращать 201 — одной проверки статуса было бы недостаточно.

The service was temporarily changed to return `Wrong title`. The positive test returned `1 failed`, comparing expected `Learn API` with actual `Wrong title`. HTTP 201 was unchanged, so a status-only check would have missed this regression.

Намеренная ошибка удалена. Полный набор повторно запущен после восстановления правильного кода.

The deliberate regression was reverted and the full suite rerun.

Это искусственная проверка чувствительности теста, не дефект стороннего продукта и не полный mutation testing.

This was a controlled sensitivity check, not an external product defect or a full mutation-testing campaign.

## Ограничения / Limitations

Проверен локальный запуск в Windows. GitHub Actions подготовлен, но результат CI пока не подтверждён. Непокрытые сценарии указаны в [контракте](api-contract.md).

Local Windows execution was verified. GitHub Actions is configured but not yet verified. See the [contract](api-contract.md) for uncovered scenarios.
