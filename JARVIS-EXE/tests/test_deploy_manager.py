import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import deploy_manager


class DeployManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "projects"
        self.project = self.root / "demo"
        self.project.mkdir(parents=True)
        self.patch_root = patch.object(deploy_manager, "ROOT", self.root)
        self.patch_root.start()

    def tearDown(self):
        self.patch_root.stop()
        self.temp.cleanup()

    def test_rejects_project_outside_workspace(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        with self.assertRaises(ValueError):
            deploy_manager.package_static_site(outside)

    def test_packages_static_site_without_running_scripts(self):
        (self.project / "index.html").write_text("<h1>Olá</h1>", encoding="utf-8")
        (self.project / "app.js").write_text("alert(1)", encoding="utf-8")
        (self.project / ".env").write_text("API_KEY=do-not-publish", encoding="utf-8")
        (self.project / "private.pem").write_text("private-key", encoding="utf-8")
        with patch.object(deploy_manager, "_run") as runner:
            archive = deploy_manager.package_static_site(self.project)
            runner.assert_not_called()
        import zipfile
        with zipfile.ZipFile(archive) as zf:
            self.assertIn("index.html", zf.namelist())
            self.assertIn("app.js", zf.namelist())
            self.assertNotIn(".env", zf.namelist())
            self.assertNotIn("private.pem", zf.namelist())

    def test_packages_prebuilt_dist_folder(self):
        dist = self.project / "dist"
        dist.mkdir()
        (dist / "index.html").write_text("<h1>Built</h1>", encoding="utf-8")
        archive = deploy_manager.package_static_site(self.project)
        import zipfile
        with zipfile.ZipFile(archive) as zf:
            self.assertIn("index.html", zf.namelist())

    def test_static_site_requires_index(self):
        with self.assertRaises(ValueError):
            deploy_manager.package_static_site(self.project)

    def test_flutter_build_uses_allowlisted_command_and_checks_artifact(self):
        (self.project / "pubspec.yaml").write_text("name: demo", encoding="utf-8")
        apk = self.project / "build/app/outputs/flutter-apk/app-release.apk"
        apk.parent.mkdir(parents=True)
        apk.write_bytes(b"apk")
        with patch.object(deploy_manager.shutil, "which", side_effect=lambda name: "C:/flutter.exe" if name == "flutter" else None), \
             patch.object(deploy_manager, "_run", return_value=subprocess.CompletedProcess([], 0, "ok", "")) as runner:
            result = deploy_manager.build_apk(self.project)
        self.assertTrue(result["success"])
        self.assertEqual(Path(result["apk"]).resolve(), apk.resolve())
        self.assertFalse(runner.call_args.args[0][0] == "cmd")

    def test_flutter_build_does_not_claim_success_without_apk(self):
        (self.project / "pubspec.yaml").write_text("name: demo", encoding="utf-8")
        with patch.object(deploy_manager.shutil, "which", return_value="C:/flutter.exe"), \
             patch.object(deploy_manager, "_run", return_value=subprocess.CompletedProcess([], 0, "ok", "")):
            result = deploy_manager.build_apk(self.project)
        self.assertFalse(result["success"])
        self.assertIsNone(result["apk"])

    def test_publish_requires_netlify_cli(self):
        (self.project / "index.html").write_text("ok", encoding="utf-8")
        with patch.object(deploy_manager.shutil, "which", return_value=None):
            with self.assertRaises(FileNotFoundError):
                deploy_manager.publish_static_site(self.project)

    def test_netlify_publish_is_non_shell_and_returns_url(self):
        (self.project / "index.html").write_text("ok", encoding="utf-8")
        completed = subprocess.CompletedProcess([], 0, '{"url":"https://demo.netlify.app"}', "")
        with patch.object(deploy_manager.shutil, "which", return_value="C:/netlify.exe"), \
             patch.object(deploy_manager, "_run", return_value=completed) as runner:
            result = deploy_manager.publish_static_site(self.project)
        self.assertTrue(result["success"])
        self.assertEqual(result["url"], "https://demo.netlify.app")
        self.assertEqual(runner.call_args.args[0][1:4], ["deploy", "--prod", "--dir"])
   


if __name__ == "__main__":
    unittest.main()
