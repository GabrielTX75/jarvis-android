import json
import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from access_control import AccessController, PERSONAL, SCHOOL


class AccessControllerTests(unittest.TestCase):
    def test_personal_profile_allows_confirmable_desktop_actions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects"
            root.mkdir()
            access = AccessController(PERSONAL, root)
            self.assertTrue(access.check("launch_app", "Code.exe"))
            self.assertTrue(access.check("capture_screen"))
            self.assertTrue(access.check("audit_folder", temp))
            self.assertFalse(access.check("admin_elevation"))

    def test_school_profile_is_limited_to_workspace_and_allowlisted_apps(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects"
            project = root / "demo"
            project.mkdir(parents=True)
            outside = Path(temp) / "Desktop"
            outside.mkdir()
            access = AccessController(SCHOOL, root)
            self.assertTrue(access.check("launch_app", "Code.exe"))
            self.assertFalse(access.check("launch_app", "powershell.exe"))
            self.assertTrue(access.check("workspace_write", project))
            self.assertFalse(access.check("workspace_write", outside))
            self.assertTrue(access.check("run_project_task", project, "flutter_analyze"))
            self.assertFalse(access.check("run_project_task", project, "python_tests"))
            self.assertFalse(access.check("capture_screen"))
            self.assertFalse(access.check("audit_folder", outside))
            self.assertTrue(access.check("audit_folder", project))
            self.assertFalse(access.check("admin_elevation"))

    def test_school_profile_does_not_grant_os_or_admin_rights(self):
        access = AccessController(SCHOOL)
        for action in ("admin_elevation", "security_bypass", "credential_dump",
                       "arbitrary_shell", "disable_security"):
            self.assertFalse(access.check(action))

    def test_access_decisions_are_audited_without_full_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects"
            root.mkdir()
            log = Path(temp) / "access.jsonl"
            access = AccessController(SCHOOL, root, log)
            access.authorize("launch_app", "Code.exe")
            event = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(event["mode"], SCHOOL)
            self.assertTrue(event["allowed"])
            self.assertEqual(event["resource"], "Code.exe")
            self.assertNotIn(str(temp), log.read_text(encoding="utf-8"))

    def test_invalid_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            AccessController("unrestricted")


if __name__ == "__main__":
    unittest.main()
