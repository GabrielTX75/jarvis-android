"""Explicit permission profiles for JARVIS EXE.

This is an application-level guardrail, not an OS sandbox. Windows account,
UAC, school-device management and filesystem ACLs remain authoritative.
"""
import json
from datetime import datetime, timezone
from pathlib import Path


PERSONAL = "personal"
SCHOOL = "school"

SCHOOL_ALLOWED_APPS = {"code.exe", "notepad.exe", "calc.exe"}
SCHOOL_ALLOWED_TASKS = {"flutter_analyze", "dart_analyze", "python_compile"}

_ALWAYS_DENIED = {
    "admin_elevation", "security_bypass", "credential_dump",
    "arbitrary_shell", "disable_security", "stealth_persistence",
}


class AccessController:
    def __init__(self, mode=PERSONAL, workspace=None, audit_path=None):
        self.workspace = Path(workspace or (Path.home() / "Documents" / "JarvisProjects")).expanduser().resolve()
        self.audit_path = Path(audit_path).expanduser() if audit_path else None
        self.set_mode(mode)

    def set_mode(self, mode):
        if mode not in {PERSONAL, SCHOOL}:
            raise ValueError("Perfil de acesso desconhecido.")
        self.mode = mode

    def _inside_workspace(self, resource):
        if resource is None:
            return False
        try:
            path = Path(resource).expanduser().resolve()
            return path == self.workspace or self.workspace in path.parents
        except (TypeError, ValueError, OSError):
            return False

    def check(self, action, resource=None, detail=None):
        if action in _ALWAYS_DENIED:
            return False
        if self.mode == PERSONAL:
            return action in {
                "launch_app", "workspace_read", "workspace_write",
                "workspace_open", "capture_screen", "audit_folder",
                "run_project_task", "browser",
            }

        # School profile is intentionally conservative and never elevates OS rights.
        if action == "launch_app":
            return Path(str(resource or "")).name.lower() in SCHOOL_ALLOWED_APPS
        if action in {"workspace_read", "workspace_write", "workspace_open"}:
            return self._inside_workspace(resource)
        if action == "run_project_task":
            return self._inside_workspace(resource) and detail in SCHOOL_ALLOWED_TASKS
        if action == "browser":
            return True
        # No screen capture, external folder audits, tests that execute project
        # code, dependency installation, deletion or administrator actions.
        return False

    def record(self, action, allowed, resource=None, detail=None):
        if self.audit_path is None:
            return
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mode": self.mode,
                "action": str(action),
                "allowed": bool(allowed),
                "resource": Path(str(resource)).name if resource else None,
                "detail": str(detail)[:100] if detail else None,
            }
            with self.audit_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False) + "\\n")
        except OSError:
            # Failure to write the optional audit log must not grant permissions.
            pass

    def authorize(self, action, resource=None, detail=None):
        allowed = self.check(action, resource, detail)
        self.record(action, allowed, resource, detail)
        return allowed
