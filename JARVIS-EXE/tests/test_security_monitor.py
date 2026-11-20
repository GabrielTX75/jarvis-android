import sys, tempfile, unittest, json, threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from security_monitor import SecurityMonitor, JsonlLogWatcher


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

    def test_jsonl_watcher_processes_new_complete_records(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "events.jsonl"
            log.write_text("", encoding="utf-8")
            monitor = SecurityMonitor(threshold=2)
            received = []
            ready = threading.Event()
            watcher = JsonlLogWatcher(str(log), monitor,
                                      on_alert=lambda alert: (received.append(alert), ready.set()),
                                      poll_seconds=0.25)
            watcher.start()
            try:
                with log.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"event_type":"login_failed","actor_id":"u"}) + "\n")
                    stream.write(json.dumps({"event_type":"login_failed","actor_id":"u"}) + "\n")
                self.assertTrue(ready.wait(3))
                self.assertEqual(received[0]["severity"], "HIGH")
            finally:
                watcher.stop()

    def test_invalid_event_rejected(self):
        with self.assertRaises(ValueError):
            SecurityMonitor().process_event({"event_type":"login_failed"})


if __name__ == "__main__":
    unittest.main()
