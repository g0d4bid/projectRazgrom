-- Схема локальной БД приложения «Разгром» (версия 1).
-- Тот же SQL выполняется на Android через пакет sqflite.

CREATE TABLE IF NOT EXISTS tasks (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  title        TEXT    NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 120),
  due_date     TEXT    NOT NULL CHECK (due_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  due_time     TEXT    CHECK (due_time IS NULL OR due_time GLOB '[0-2][0-9]:[0-5][0-9]'),
  priority     INTEGER NOT NULL DEFAULT 1 CHECK (priority IN (0, 1, 2)),
  is_done      INTEGER NOT NULL DEFAULT 0 CHECK (is_done IN (0, 1)),
  remind       INTEGER NOT NULL DEFAULT 1 CHECK (remind IN (0, 1)),
  created_at   TEXT    NOT NULL,
  updated_at   TEXT    NOT NULL
);

-- Экраны «Сегодня» и «Неделя» выбирают задачи по дате или диапазону дат
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks (due_date, due_time);

-- Настройки уведомлений (reminders_enabled, minutes_before) хранятся не в БД,
-- а в хранилище «ключ – значение» shared_preferences.

PRAGMA user_version = 1;
