import sys, tempfile, unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from security_monitor import SecurityMonitor


class SecurityMonitorTests(unittest.TestCase):
    def test_repeated_failed_logins_raise_alert(self):
        monitor = SecurityMonitor(threshold=3, window_seconds=60)
        base = datetime.now(timezone.utc)
        alerts = []
        for i in range(3):
            alert = monitor.process_event({
                "event_type": "login_failed", "actor_id": "account-1",
                "timestamp": (base + timedelta(seconds=i)).isoformat()
            })
            if alert:
                alerts.append(alert)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["severity"], "HIGH")
        self.assertEqual(alerts[0]["action"], "DRY_RUN_ONLY")

    def test_old_failures_expire(self):
        monitor = SecurityMonitor(threshold=3, window_seconds=10)
        base = datetime.now(timezone.utc)
        monitor.process_event({"event_type":"login_failed","actor_id":"a",
                               "timestamp":base.isoformat()})
        monitor.process_event({"event_type":"login_failed","actor_id":"a",
                               "timestamp":(base+timedelta(seconds=1)).isoformat()})
        result = monitor.process_event({"event_type":"login_failed","actor_id":"a",
                                        "timestamp":(base+timedelta(seconds=30)).isoformat()})
        self.assertIsNone(result)

    def test_sensitive_event_alerts_without_remote_action(self):
        monitor = SecurityMonitor()
        alert = monitor.process_event({"event_type":"admin_role_granted","actor_id":"user-2"})
        self.assertEqual(alert["action"], "DRY_RUN_ONLY")

    def test_invalid_event_rejected(self):
        with self.assertRaises(ValueError):
            SecurityMonitor().process_event({"event_type":"login_failed"})


if __name__ == "__main__":
    unittest.main()
