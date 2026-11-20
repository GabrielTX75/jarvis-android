"""Provider-neutral defensive event monitor for JARVIS.

Consumes normalized JSONL security events exported by an application/server.
It never scans networks or attacks a source address. Containment is delegated
to an explicitly configured project adapter; without one, actions are dry-run.
"""
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import threading


class SecurityMonitor:
    def __init__(self, threshold=5, window_seconds=300, response_adapter=None,
                 auto_contain=False):
        if threshold < 2 or window_seconds < 1:
            raise ValueError("Limites de detecção inválidos.")
        self.threshold = threshold
        self.window = timedelta(seconds=window_seconds)
        self.response_adapter = response_adapter
        self.auto_contain = bool(auto_contain and response_adapter)
        self.failures = defaultdict(deque)
        self.alerts = []

    @staticmethod
    def _time(value):
        if not value:
            return datetime.now(timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def process_event(self, event):
        if not isinstance(event, dict):
            raise ValueError("Evento precisa ser um objeto JSON.")
        kind = str(event.get("event_type", "")).strip().lower()
        actor = str(event.get("actor_id", "")).strip()
        if not kind or not actor:
            raise ValueError("Evento precisa conter event_type e actor_id.")
        now = self._time(event.get("timestamp"))
        reason = None
        severity = "LOW"

        if kind in {"login_failed", "auth_failed"}:
            queue = self.failures[actor]
            cutoff = now - self.window
            while queue and queue[0] < cutoff:
                queue.popleft()
            queue.append(now)
            if len(queue) >= self.threshold:
                severity = "HIGH"
                reason = f"{len(queue)} falhas de autenticação dentro da janela configurada"
        elif kind in {"privilege_escalation", "admin_role_granted", "security_policy_changed"}:
            severity = "HIGH"
            reason = "evento sensível de privilégio ou política"
        elif kind in {"rate_limit_triggered", "suspicious_access"}:
            severity = "MEDIUM"
            reason = "evento suspeito reportado pelo serviço conectado"

        if not reason:
            return None

        alert = {
            "timestamp": now.isoformat(),
            "severity": severity,
            "event_type": kind,
            "actor_id": actor,
            "reason": reason,
            "project_id": str(event.get("project_id", "unbound")),
            "action": "ALERT_ONLY",
        }
        if self.auto_contain and severity == "HIGH":
            # Adapter must be supplied by the owner and scoped to their own project.
            result = self.response_adapter.contain_actor(actor, reason)
            alert["action"] = "CONTAINED" if result is True else "CONTAINMENT_FAILED"
        elif severity == "HIGH":
            alert["action"] = "DRY_RUN_ONLY"
        self.alerts.append(alert)
        return alert


class JsonlLogWatcher:
    """Poll an owner-provided JSONL audit log and forward new events."""
    def __init__(self, path, monitor, on_alert=None, poll_seconds=1.0):
        self.path = Path(path).expanduser().resolve()
        self.monitor = monitor
        self.on_alert = on_alert
        self.poll_seconds = max(0.25, float(poll_seconds))
        self._stop = threading.Event()
        self._thread = None
        self._offset = 0
        self._pending = ""

    def start(self):
        if not self.path.is_file():
            raise FileNotFoundError("Arquivo de log do projeto não encontrado.")
        if self._thread and self._thread.is_alive():
            return
        self._offset = self.path.stat().st_size
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self):
        while not self._stop.wait(self.poll_seconds):
            try:
                size = self.path.stat().st_size
                if size < self._offset:
                    self._offset = 0  # log rotated/truncated
                with self.path.open("r", encoding="utf-8") as stream:
                    stream.seek(self._offset)
                    chunk = stream.read()
                    self._offset = stream.tell()
                parts = (self._pending + chunk).splitlines(keepends=True)
                self._pending = ""
                for part in parts:
                    if not part.endswith(("\\n", "\\r")):
                        self._pending = part
                        continue
                    line = part.strip()
                    if not line:
                        continue
                    try:
                        alert = self.monitor.process_event(json.loads(line))
                        if alert and self.on_alert:
                            self.on_alert(alert)
                    except (ValueError, json.JSONDecodeError):
                        continue
            except OSError:
                # Temporary log rotation/permission errors are retried next poll.
                continue
