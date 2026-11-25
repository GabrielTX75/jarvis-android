"""Safe, project-local Python environment helpers for JARVIS EXE."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_PACKAGE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z")


class EnvironmentInstallError(RuntimeError):
    """A safe, non-sensitive installation failure."""


def validate_package_name(package):
    """Accept one package name only; reject flags, URLs and shell text."""
    if not isinstance(package, str) or not _PACKAGE_NAME.fullmatch(package.strip()):
        raise ValueError("Informe somente um nome de pacote PyPI válido.")
    return package.strip()


def resolve_python_launcher(frozen=None, executable=None, which=None):
    """Find a system Python; never use a PyInstaller executable as Python."""
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    if executable is None:
        executable = sys.executable
    if which is None:
        which = shutil.which
    if not frozen:
        return [str(executable)] if executable else None
    launcher = which("py.exe") or which("py")
    if launcher:
        return [str(launcher), "-3"]
    interpreter = which("python.exe") or which("python")
    if interpreter:
        return [str(interpreter)]
    return None


def project_venv_path(project_dir):
    return Path(project_dir).expanduser().resolve() / ".venv"


def venv_interpreter_path(project_dir, windows=None):
    if windows is None:
        windows = os.name == "nt"
    venv_dir = project_venv_path(project_dir)
    relative = Path("Scripts") / "python.exe" if windows else Path("bin") / "python"
    return venv_dir / relative


def validate_project_venv(project_dir, windows=None):
    """Return (venv_dir, interpreter), rejecting symlinks that escape the project."""
    project = Path(project_dir).expanduser().resolve()
    if not project.is_dir():
        raise ValueError("Escolha uma pasta de projeto existente.")
    venv_dir = project_venv_path(project)
    interpreter = venv_interpreter_path(project, windows=windows)
    try:
        venv_dir.resolve().relative_to(project)
        interpreter.resolve().relative_to(venv_dir.resolve())
    except (OSError, ValueError, RuntimeError):
        raise ValueError("O ambiente .venv aponta para fora da pasta do projeto.")
    return venv_dir, interpreter


def build_venv_command(launcher, venv_dir):
    return [*launcher, "-m", "venv", str(venv_dir)]


def build_pip_install_command(interpreter, package):
    safe_package = validate_package_name(package)
    return [
        str(interpreter), "-m", "pip", "install",
        "--disable-pip-version-check", "--no-input", safe_package,
    ]


def install_package_in_project(project_dir, package, launcher, runner=None, windows=None):
    """Create/reuse a project .venv and install one validated package.

    Process output is deliberately discarded: pip configuration may contain
    private index URLs or credentials. Only generic failures are raised.
    """
    if runner is None:
        runner = subprocess.run
    safe_package = validate_package_name(package)
    if not launcher:
        raise EnvironmentInstallError(
            "Python 3 externo não foi encontrado. Instale Python 3 e habilite 'py' ou 'python'."
        )

    venv_dir, interpreter = validate_project_venv(project_dir, windows=windows)
    if venv_dir.exists() and not interpreter.is_file():
        raise EnvironmentInstallError(
            "A pasta .venv já existe, mas está incompleta. Ela não foi sobrescrita."
        )

    if not venv_dir.exists():
        created = runner(
            build_venv_command(launcher, venv_dir),
            shell=False, capture_output=True, text=True, timeout=180, check=False,
        )
        if created.returncode != 0 or not interpreter.is_file():
            raise EnvironmentInstallError(
                "Não foi possível criar o ambiente .venv. Verifique a instalação do Python 3 e as permissões da pasta."
            )

    installed = runner(
        build_pip_install_command(interpreter, safe_package),
        shell=False, capture_output=True, text=True, timeout=300, check=False,
    )
    if installed.returncode != 0:
        raise EnvironmentInstallError(
            f"O pip terminou com código {installed.returncode}. Verifique o pacote, a conexão e a configuração do Python/pip."
        )
    return venv_dir, interpreter
