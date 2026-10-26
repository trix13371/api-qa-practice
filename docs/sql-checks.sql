-- Read-only checks for a LOCAL practice database. No passwords or tokens are selected.

-- 1. Tasks and their owners: compare id/title/completed with API responses.
SELECT t.id, u.username AS owner, t.title, t.completed
FROM tasks AS t
JOIN users AS u ON u.id = t.owner_id
ORDER BY t.id;

-- 2. Task counts, including users with no tasks.
SELECT u.username, COUNT(t.id) AS task_count,
       SUM(CASE WHEN t.completed = 1 THEN 1 ELSE 0 END) AS completed_count
FROM users AS u
LEFT JOIN tasks AS t ON t.owner_id = u.id
GROUP BY u.id, u.username
ORDER BY u.id;

-- 3. Orphan tasks: expected empty result.
SELECT t.id, t.owner_id
FROM tasks AS t
LEFT JOIN users AS u ON u.id = t.owner_id
WHERE u.id IS NULL;

-- 4. Basic stored-field integrity: expected empty result.
-- This is not an exhaustive replacement for the Python Unicode validation.
SELECT id, title, completed
FROM tasks
WHERE title IS NULL OR length(title) NOT BETWEEN 1 AND 100
   OR instr(title, char(0)) > 0 OR completed NOT IN (0, 1);
