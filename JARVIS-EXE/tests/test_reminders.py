import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from reminders import ReminderManager, parse_reminder

class ReminderTests(unittest.TestCase):
    def test_parse_meeting_at_three(self):
        now = datetime(2026, 11, 21, 12, 0)
        result = parse_reminder("me avisa na minha reunião às 15 h", now)
        self.assertIsNotNone(result)
        title, when = result
        self.assertIn("reunião", title.lower())
        self.assertEqual(when, datetime(2026, 11, 21, 15, 0))

    def test_parse_tomorrow(self):
        now = datetime(2026, 11, 21, 12, 0)
        _, when = parse_reminder("me lembra da consulta amanhã às 9:30", now)
        self.assertEqual(when, datetime(2026, 11, 22, 9, 30))

    def test_alert_is_ten_minutes_early(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = ReminderManager(Path(tmp) / "reminders.json")
            event = datetime(2026, 11, 21, 15, 0)
            item = manager.add("Reunião", event)
            self.assertEqual(datetime.fromisoformat(item["notify_at"]), event - timedelta(minutes=10))
            self.assertEqual(manager.due(event - timedelta(minutes=11)), [])
            self.assertEqual(len(manager.due(event - timedelta(minutes=10))), 1)
            self.assertEqual(manager.due(event - timedelta(minutes=9)), [])

    def test_cancelled_reminder_does_not_fire(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = ReminderManager(Path(tmp) / "reminders.json")
            item = manager.add("Reunião", datetime(2026, 11, 21, 15, 0))
            manager.cancel(item["id"])
            self.assertEqual(manager.due(datetime(2026, 11, 21, 14, 50)), [])

if __name__ == "__main__":
    unittest.main()
