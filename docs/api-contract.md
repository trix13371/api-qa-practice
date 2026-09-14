# Task API contract / Требования к API

This is a local training service with in-memory storage. Restarting it clears all tasks. It has no login, database, real users, or external dependencies at runtime.

Это локальный учебный сервис: задачи хранятся в памяти и исчезают после перезапуска. Авторизации и базы данных нет.

| Request / Запрос | Success / Успех | Error / Ошибка |
| --- | --- | --- |
| GET /tasks | 200, JSON array; initially [] / JSON-массив, вначале [] | — |
| POST /tasks | 201, created task / созданная задача | 400 for invalid input / при неверных данных |
| GET /tasks/{id} | 200, requested task / выбранная задача | 404 if the numeric ID does not exist / если числовой ID не найден |

## Creation / Создание

Send a JSON object with a required string field `title`. Empty and whitespace-only titles are rejected. Other characters are allowed, including `@@@`. The original non-empty title is preserved. Additional fields are ignored; `id` and `completed` are always server-assigned.

Передаётся JSON-объект с обязательным строковым полем `title`. Пустая строка и строка только из пробелов недопустимы. Остальные символы, включая `@@@`, разрешены. Непустое название сохраняется как передано. Дополнительные поля игнорируются; `id` и `completed` назначает сервер.

```json
{"title": "Learn API"}
```

Example response / Пример ответа:

```json
{"id": 1, "title": "Learn API", "completed": false}
```

IDs are positive integers, unique within a server instance. New tasks are incomplete. The list is returned in creation order. Rejected requests must not create, remove, or modify saved tasks.

ID — положительные целые числа, уникальные в пределах экземпляра сервера. Новая задача не выполнена. Список возвращается в порядке создания. Отклонённый запрос не должен создавать, удалять или изменять задачи.

Missing, empty, or non-string title / Нет title, пустое или нестроковое значение:

```json
{"error": "title must be a non-empty string"}
```

Missing/malformed JSON or a non-object body / Отсутствующий или некорректный JSON либо тело не является объектом:

```json
{"error": "JSON object required"}
```

Unknown numeric task ID / Неизвестный числовой ID:

```json
{"error": "Task not found"}
```

## Scope / Объём

The initial automated suite covers creation, reading, and three invalid-title cases. Missing-ID errors, whitespace-only titles, malformed JSON, extra fields, updates, deletion, concurrency, and persistence are not covered by these two tests. Update and delete endpoints are not implemented yet.

Первые автотесты проверяют создание, чтение и три варианта неверного title. В них не покрыты неизвестный ID, пробельное название, некорректный JSON, дополнительные поля, изменение, удаление, параллельные запросы и постоянное хранение. Методы изменения и удаления пока не реализованы.
