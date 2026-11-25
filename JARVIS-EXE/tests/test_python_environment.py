import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from python_environment import (
    EnvironmentInstallError,
    build_pip_install_command,
    build_venv_command,
    install_package_in_project,
    project_venv_path,
    resolve_python_launcher,
    validate_package_name,
    validate_project_venv,
    venv_interpreter_path,
)


class PythonEnvironmentTests(unittest.TestCase):
    def test_frozen_build_prefers_python_launcher(self):
        found = {"py.exe": r"C:\Windows\py.exe", "python.exe": r"C:\Python\python.exe"}
        result = resolve_python_launcher(True, r"C:\Apps\JARVIS.exe", lambda name: found.get(name))
        self.assertEqual(result, [r"C:\Windows\py.exe", "-3"])

    def test_frozen_build_falls_back_to_python_executable(self):
        result = resolve_python_launcher(
            True, r"C:\Apps\JARVIS.exe",
            lambda name: r"C:\Python\python.exe" if name == "python.exe" else None
        )
        self.assertEqual(result, [r"C:\Python\python.exe"])

    def test_frozen_build_without_system_python_is_blocked(self):
        self.assertIsNone(resolve_python_launcher(True, r"C:\Apps\JARVIS.exe", lambda _: None))

    def test_source_mode_uses_current_interpreter(self):
        self.assertEqual(
            resolve_python_launcher(False, "/usr/bin/python3", lambda _: None),
            ["/usr/bin/python3"]
        )

    def test_package_name_rejects_flags_urls_and_shell_text(self):
        for value in ("--index-url", "https://example.test/pkg", "pkg;whoami", "pkg extra", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_package_name(value)
        self.assertEqual(validate_package_name("Pillow_Extra-2.0"), "Pillow_Extra-2.0")

    def test_venv_and_pip_commands_are_argument_lists(self):
        with tempfile.TemporaryDirectory() as folder:
            venv = project_venv_path(folder)
            python = venv_interpreter_path(folder, windows=True)
            self.assertEqual(
                build_venv_command(["py.exe", "-3"], venv),
                ["py.exe", "-3", "-m", "venv", str(venv)]
            )
            self.assertEqual(
                build_pip_install_command(python, "requests"),
                [str(python), "-m", "pip", "install",
                 "--disable-pip-version-check", "--no-input", "requests"]
            )

    def test_venv_interpreter_path_is_platform_specific(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(str(venv_interpreter_path(folder, True)).endswith("Scripts/python.exe"))
            self.assertTrue(str(venv_interpreter_path(folder, False)).endswith("bin/python"))

    def test_existing_venv_path_must_stay_inside_project(self):
        with tempfile.TemporaryDirectory() as folder:
            venv, interpreter = validate_project_venv(folder, True)
            self.assertEqual(venv, Path(folder).resolve() / ".venv")
            self.assertEqual(interpreter, venv / "Scripts" / "python.exe")

    def test_install_creates_project_venv_then_installs_package(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            expected_venv = project_venv_path(folder)
            expected_python = venv_interpreter_path(folder, True)

            def fake_runner(command, **kwargs):
                calls.append((command, kwargs))
                if "-m" in command and "venv" in command:
                    expected_python.parent.mkdir(parents=True)
                    expected_python.write_text("test interpreter", encoding="utf-8")
                return SimpleNamespace(returncode=0)

            venv, interpreter = install_package_in_project(
                folder, "requests", ["py.exe", "-3"], runner=fake_runner, windows=True
            )
            self.assertEqual(venv, expected_venv)
            self.assertEqual(interpreter, expected_python)
            self.assertEqual(len(calls), 2)
            self.assertIn("venv", calls[0][0])
            self.assertIn("pip", calls[1][0])
            self.assertFalse(calls[0][1]["shell"])
            self.assertFalse(calls[1][1]["shell"])
            self.assertTrue(calls[0][1]["capture_output"])
            self.assertTrue(calls[1][1]["capture_output"])

    def test_existing_venv_is_reused_without_recreating(self):
        with tempfile.TemporaryDirectory() as folder:
            python = venv_interpreter_path(folder, True)
            python.parent.mkdir(parents=True)
            python.write_text("test interpreter", encoding="utf-8")
            calls = []

            def fake_runner(command, **kwargs):
                calls.append(command)
                return SimpleNamespace(returncode=0)

            install_package_in_project(folder, "requests", ["py.exe", "-3"],
                                        runner=fake_runner, windows=True)
            self.assertEqual(len(calls), 1)
            self.assertIn("pip", calls[0])

    def test_incomplete_venv_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            project_venv_path(folder).mkdir()
            calls = []
            with self.assertRaises(EnvironmentInstallError):
                install_package_in_project(folder, "requests", ["py.exe", "-3"],
                                            runner=lambda *a, **k: calls.append(a), windows=True)
            self.assertEqual(calls, [])

    def test_venv_creation_failure_does_not_run_pip(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            def fake_runner(command, **kwargs):
                calls.append(command)
                return SimpleNamespace(returncode=1)
            with self.assertRaises(EnvironmentInstallError):
                install_package_in_project(folder, "requests", ["py.exe", "-3"],
                                            runner=fake_runner, windows=True)
            self.assertEqual(len(calls), 1)
            self.assertIn("venv", calls[0])

    def test_pip_failure_is_reported_without_raw_output(self):
        with tempfile.TemporaryDirectory() as folder:
            python = venv_interpreter_path(folder, True)
            calls = []
            def fake_runner(command, **kwargs):
                calls.append(command)
                if "venv" in command:
                    python.parent.mkdir(parents=True)
                    python.write_text("test interpreter", encoding="utf-8")
                    return SimpleNamespace(returncode=0)
                return SimpleNamespace(returncode=23, stdout="https://user:secret@example.test", stderr="token=private")
            with self.assertRaisesRegex(EnvironmentInstallError, "código 23") as raised:
                install_package_in_project(folder, "requests", ["py.exe", "-3"],
                                            runner=fake_runner, windows=True)
            self.assertNotIn("secret", str(raised.exception))
            self.assertNotIn("private", str(raised.exception))
            self.assertEqual(len(calls), 2)

    def test_no_system_python_fails_before_any_process(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(EnvironmentInstallError):
                install_package_in_project(folder, "requests", None,
                                           runner=lambda *a, **k: self.fail("runner should not run"),
                                           windows=True)


if __name__ == "__main__":
    unittest.main()
