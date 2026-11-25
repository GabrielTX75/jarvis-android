import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import vscode_integration


class VscodeIntegrationTests(unittest.TestCase):
    def test_manifest_writes_files_inside_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "projects"
            with patch.object(vscode_integration, "ROOT", root), \
                 patch.object(vscode_integration, "create_project") as create, \
                 patch.object(vscode_integration, "write_project_file") as write:
                create.return_value = root / "demo"
                write.return_value = root / "demo" / "main.dart"
                path, files = vscode_integration.create_generated_project(
                    "demo", [{"path": "lib/main.dart", "content": "void main() {}"}]
                )
                create.assert_called_once_with("demo")
                write.assert_called_once_with("demo", "lib/main.dart", "void main() {}")
                self.assertEqual(path, root / "demo")
                self.assertEqual(len(files), 1)

    def test_manifest_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            vscode_integration.create_generated_project(
                "demo", [{"path": "../outside.txt", "content": "no"}]
            )

    def test_manifest_rejects_executable_files(self):
        with self.assertRaises(ValueError):
            vscode_integration.create_generated_project(
                "demo", [{"path": "run.exe", "content": "binary"}]
            )

    def test_manifest_rejects_duplicate_paths(self):
        with self.assertRaises(ValueError):
            vscode_integration.create_generated_project(
                "demo", [
                    {"path": "main.py", "content": "print(1)"},
                    {"path": "main.py", "content": "print(2)"},
                ]
            )

    def test_open_uses_no_shell(self):
        with patch.object(vscode_integration, "find_vscode", return_value="C:/VSCode/Code.exe"), \
             patch.object(vscode_integration.subprocess, "Popen") as popen, \
             patch.object(Path, "mkdir"):
            vscode_integration.open_in_vscode("C:/Projects/demo")
            args, kwargs = popen.call_args
            self.assertEqual(args[0][0], "C:/VSCode/Code.exe")
            self.assertFalse(kwargs["shell"])


    def test_project_task_is_allowlisted_and_uses_no_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "projects"
            project = workspace / "demo"
            project.mkdir(parents=True)
            with patch.object(vscode_integration, "ROOT", workspace), \
                 patch.object(vscode_integration.shutil, "which", return_value="C:/Flutter/bin/flutter.exe"), \
                 patch.object(vscode_integration.subprocess, "run") as runner:
                runner.return_value = __import__("subprocess").CompletedProcess(
                    ["flutter", "analyze", "--no-pub"], 0, "No issues found", ""
                )
                result = vscode_integration.run_project_task(project, "flutter_analyze")
                self.assertEqual(result.returncode, 0)
                args, kwargs = runner.call_args
                self.assertEqual(args[0], ["C:/Flutter/bin/flutter.exe", "analyze", "--no-pub"])
                self.assertFalse(kwargs["shell"])

    def test_project_task_rejects_paths_outside_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "projects"
            outside = Path(temp) / "outside"
            workspace.mkdir()
            outside.mkdir()
            with patch.object(vscode_integration, "ROOT", workspace):
                with self.assertRaises(ValueError):
                    vscode_integration.run_project_task(outside, "python_compile")

    def test_project_task_rejects_arbitrary_commands(self):
        with self.assertRaises(ValueError):
            vscode_integration.run_project_task(".", "arbitrary_shell")


if __name__ == "__main__":
    unittest.main()
