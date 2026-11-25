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


if __name__ == "__main__":
    unittest.main()
