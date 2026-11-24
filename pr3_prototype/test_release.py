import sqlite3
import unittest
from datetime import datetime
from razgrom_core import Task, TaskRepository, ReminderPlanner


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.repo = TaskRepository(":memory:")
        self.addCleanup(self.repo.close)

    def rejected(self, day, time):
        bad = Task("Ошибка", day, time)
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.create(bad)
        original = Task("Дело", "2028-02-29", "23:59")
        self.repo.create(original)
        original.due_date, original.due_time = day, time
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.update(original)
        stored = self.repo.get(original.id)
        self.assertEqual((stored.due_date, stored.due_time), ("2028-02-29", "23:59"))
        self.assertEqual(self.repo.db.execute("SELECT count(*) FROM tasks").fetchone()[0], 1)

    def test_impossible_date(self):
        self.rejected("2026-02-30", "10:00")

    def test_invalid_hour(self):
        self.rejected("2026-11-25", "24:00")

    def test_legacy_record_does_not_block_plan(self):
        bad = Task("Старая запись", "2026-02-30", "29:10", id=1)
        good = Task("Дело", "2028-02-29", "23:59", id=2)
        self.assertEqual(ReminderPlanner(5).plan([bad, good], datetime(2026,1,1)),
                         {2: datetime(2028,2,29,23,54)})

    def test_completion_and_deletion(self):
        task = Task("Дело", "2028-02-29", "23:59")
        self.repo.create(task)
        self.repo.set_done(task.id, True)
        self.assertTrue(self.repo.get(task.id).is_done)
        self.assertEqual(self.repo.active_with_reminders(), [])
        self.repo.set_done(task.id, False)
        self.assertEqual(len(self.repo.active_with_reminders()), 1)
        self.repo.delete(task.id)
        self.assertEqual(self.repo.active_with_reminders(), [])
