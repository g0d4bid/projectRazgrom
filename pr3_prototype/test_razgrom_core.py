"""Проверка реализуемости архитектурных решений ПР №3 на прототипе слоя данных."""
import random
import sqlite3
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from razgrom_core import HIGH, LOW, MEDIUM, ReminderPlanner, Task, TaskRepository, week_of


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'razgrom.db'
        self.repo = TaskRepository(self.path)

    def tearDown(self):
        self.repo.close()
        self.tmp.cleanup()

    def test_1_crud(self):
        """US-02: создание, изменение и удаление задачи."""
        tid = self.repo.create(Task('Сдать ПР №3', '2026-11-12', '10:00', HIGH))
        task = self.repo.get(tid)
        self.assertEqual(task.title, 'Сдать ПР №3')
        task.due_time = '11:30'
        self.repo.update(task)
        self.assertEqual(self.repo.get(tid).due_time, '11:30')
        self.repo.delete(tid)
        self.assertIsNone(self.repo.get(tid))

    def test_2_survives_restart(self):
        """US-02, TSK-03: задача сохраняется после закрытия и повторного открытия БД."""
        tid = self.repo.create(Task('Купить продукты', '2026-11-12', '18:00'))
        self.repo.close()
        self.repo = TaskRepository(self.path)  # «перезапуск приложения»
        self.assertEqual(self.repo.get(tid).title, 'Купить продукты')

    def test_3_today_order(self):
        """US-01: порядок списка «Сегодня» – по времени, затем по приоритету; выполненные внизу."""
        day = '2026-11-12'
        self.repo.create(Task('Без времени', day, None, HIGH))
        self.repo.create(Task('Вечер', day, '19:00', LOW))
        self.repo.create(Task('Утро, низкий', day, '09:00', LOW))
        self.repo.create(Task('Утро, высокий', day, '09:00', HIGH))
        done = self.repo.create(Task('Уже сделано', day, '08:00', MEDIUM))
        self.repo.set_done(done, True)
        self.repo.create(Task('Другой день', '2026-11-13', '09:00'))
        titles = [t.title for t in self.repo.for_day(day)]
        self.assertEqual(titles, ['Утро, высокий', 'Утро, низкий', 'Вечер', 'Без времени', 'Уже сделано'])

    def test_4_week_counts(self):
        """US-05: количество задач по дням недели."""
        first, last = week_of(date(2026, 11, 12))
        self.assertEqual((first, last), ('2026-11-09', '2026-11-15'))
        for d in ('2026-11-09', '2026-11-12', '2026-11-12', '2026-11-16'):
            self.repo.create(Task('Задача', d, '12:00'))
        self.assertEqual(self.repo.count_by_day(first, last), {'2026-11-09': 1, '2026-11-12': 2})

    def test_5_rejects_bad_input(self):
        """Безопасность и целостность: БД не принимает пустое название, неверную дату и приоритет."""
        for bad in (Task('   ', '2026-11-12'), Task('Ок', '12.11.2026'), Task('Ок', '2026-11-12', priority=7)):
            with self.assertRaises(sqlite3.IntegrityError):
                self.repo.create(bad)

    def test_6_sql_injection_is_harmless(self):
        """Параметризованные запросы: текст с SQL не выполняется."""
        evil = "x'); DROP TABLE tasks; --"
        tid = self.repo.create(Task(evil, '2026-11-12', '10:00'))
        self.assertEqual(self.repo.get(tid).title, evil)
        self.assertEqual(len(self.repo.for_day('2026-11-12')), 1)

    def test_7_today_is_fast(self):
        """Производительность: выборка «Сегодня» среди 5000 задач."""
        rnd = random.Random(1)
        start = date(2026, 9, 1)
        with self.repo.db:
            for i in range(5000):
                d = (start + timedelta(days=rnd.randrange(180))).isoformat()
                self.repo.db.execute(
                    'INSERT INTO tasks (title, due_date, due_time, priority, created_at, updated_at) '
                    'VALUES (?, ?, ?, ?, ?, ?)',
                    (f'Задача {i}', d, f'{rnd.randrange(24):02d}:{rnd.randrange(60):02d}', rnd.randrange(3), d, d))
        t0 = time.perf_counter()
        for _ in range(100):
            self.repo.for_day('2026-11-12')
        avg_ms = (time.perf_counter() - t0) * 1000 / 100
        print(f'\n    средняя выборка «Сегодня» из 5000 задач: {avg_ms:.2f} мс', end=' ')
        self.assertLess(avg_ms, 50)


class ReminderTest(unittest.TestCase):
    def test_8_plan(self):
        """US-03: напоминания только для активных задач со временем в будущем; учитывается смещение."""
        now = datetime(2026, 11, 12, 12, 0)
        tasks = [
            Task('Будущая', '2026-11-12', '15:00', id=1),
            Task('Прошедшая', '2026-11-12', '09:00', id=2),
            Task('Выполненная', '2026-11-12', '16:00', is_done=True, id=3),
            Task('Без напоминания', '2026-11-12', '17:00', remind=False, id=4),
            Task('Без времени', '2026-11-12', None, id=5),
        ]
        plan = ReminderPlanner(minutes_before=15).plan(tasks, now)
        self.assertEqual(plan, {1: datetime(2026, 11, 12, 14, 45)})


if __name__ == '__main__':
    unittest.main(verbosity=2)
