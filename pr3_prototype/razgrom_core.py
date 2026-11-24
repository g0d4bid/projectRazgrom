"""Прототип слоя данных и логики напоминаний приложения «Разгром».

Повторяет интерфейсы, которые затем будут реализованы на Dart во Flutter-приложении:
TaskRepository (работа с SQLite) и ReminderPlanner (расчёт времени напоминаний).
"""
import sqlite3
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

SCHEMA = Path(__file__).with_name('schema.sql')

LOW, MEDIUM, HIGH = 0, 1, 2


@dataclass
class Task:
    title: str
    due_date: str              # ГГГГ-ММ-ДД
    due_time: str | None = None  # ЧЧ:ММ, None – задача на весь день
    priority: int = MEDIUM
    is_done: bool = False
    remind: bool = True
    id: int | None = None


class TaskRepository:
    """Единственная точка доступа к таблице tasks."""

    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA.read_text(encoding='utf-8'))

    def close(self):
        self.db.close()

    def create(self, task: Task) -> int:
        validate_deadline(task)
        now = datetime.now().isoformat(timespec='seconds')
        with self.db:  # транзакция
            cur = self.db.execute(
                'INSERT INTO tasks (title, due_date, due_time, priority, is_done, remind, created_at, updated_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (task.title.strip(), task.due_date, task.due_time, task.priority,
                 int(task.is_done), int(task.remind), now, now))
        task.id = cur.lastrowid
        return task.id

    def update(self, task: Task):
        validate_deadline(task)
        with self.db:
            self.db.execute(
                'UPDATE tasks SET title = ?, due_date = ?, due_time = ?, priority = ?, is_done = ?, remind = ?, '
                'updated_at = ? WHERE id = ?',
                (task.title.strip(), task.due_date, task.due_time, task.priority, int(task.is_done),
                 int(task.remind), datetime.now().isoformat(timespec='seconds'), task.id))

    def set_done(self, task_id: int, done: bool):
        with self.db:
            self.db.execute('UPDATE tasks SET is_done = ?, updated_at = ? WHERE id = ?',
                            (int(done), datetime.now().isoformat(timespec='seconds'), task_id))

    def delete(self, task_id: int):
        with self.db:
            self.db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))

    def get(self, task_id: int) -> Task | None:
        row = self.db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
        return _to_task(row) if row else None

    def for_day(self, day: str) -> list[Task]:
        """Экран «Сегодня»: невыполненные выше, затем по времени (без времени – в конце), затем по приоритету."""
        rows = self.db.execute(
            'SELECT * FROM tasks WHERE due_date = ? '
            'ORDER BY is_done, due_time IS NULL, due_time, priority DESC, id', (day,)).fetchall()
        return [_to_task(r) for r in rows]

    def count_by_day(self, first: str, last: str) -> dict[str, int]:
        """Экран «Неделя»: количество задач по дням диапазона."""
        rows = self.db.execute(
            'SELECT due_date, COUNT(*) AS n FROM tasks WHERE due_date BETWEEN ? AND ? GROUP BY due_date',
            (first, last)).fetchall()
        return {r['due_date']: r['n'] for r in rows}

    def active_with_reminders(self) -> list[Task]:
        rows = self.db.execute(
            'SELECT * FROM tasks WHERE is_done = 0 AND remind = 1 AND due_time IS NOT NULL').fetchall()
        return [_to_task(r) for r in rows]


def validate_deadline(task):
    try:
        if date.fromisoformat(task.due_date).isoformat() != task.due_date:
            raise ValueError
        if task.due_time is not None:
            if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", task.due_time):
                raise ValueError
    except (ValueError, TypeError) as exc:
        raise sqlite3.IntegrityError("Проверьте дату (ГГГГ-ММ-ДД) и время (ЧЧ:ММ)") from exc


def _to_task(row) -> Task:
    return Task(id=row['id'], title=row['title'], due_date=row['due_date'], due_time=row['due_time'],
                priority=row['priority'], is_done=bool(row['is_done']), remind=bool(row['remind']))


class ReminderPlanner:
    """Решает, какие уведомления должны быть запланированы в ОС и на какое время.

    Идентификатор уведомления совпадает с id задачи, поэтому отмена и перенос выполняются по id.
    """

    def __init__(self, minutes_before: int = 0):
        self.minutes_before = minutes_before

    def fire_time(self, task: Task) -> datetime | None:
        if task.is_done or not task.remind or task.due_time is None:
            return None
        try:
            validate_deadline(task)
            due = datetime.fromisoformat(f'{task.due_date}T{task.due_time}')
        except (ValueError, sqlite3.IntegrityError):
            return None  # Одна старая ошибочная запись не отменяет остальные напоминания.
        return due - timedelta(minutes=self.minutes_before)

    def plan(self, tasks: list[Task], now: datetime) -> dict[int, datetime]:
        """Полный план уведомлений (используется после перезагрузки телефона и смены настроек)."""
        result = {}
        for t in tasks:
            at = self.fire_time(t)
            if at is not None and at > now:
                result[t.id] = at
        return result


def week_of(day: date) -> tuple[str, str]:
    monday = day - timedelta(days=day.weekday())
    return monday.isoformat(), (monday + timedelta(days=6)).isoformat()
