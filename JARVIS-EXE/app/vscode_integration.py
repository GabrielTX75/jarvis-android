"""Safe VS Code integration and generated-project workspace actions.

Generated files are written only inside the JARVIS project directory. This
module never executes generated code or shell commands.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from project_workspace import ROOT, create_project, write_project_file

_BLOCKED_SUFFIXES = {
    ".exe", ".dll", ".msi", ".com", ".scr", ".bat", ".cmd",
    ".ps1", ".vbs", ".wsf", ".lnk", ".sys",
}
_MAX_FILES = 40
_MAX_FILE_BYTES = 500_000
_MAX_TOTAL_BYTES = 2_000_000


def find_vscode():
    """Return a trusted VS Code executable path, or None when unavailable."""
    candidates = []
    on_windows = os.name == "nt"
    if on_windows:
        local = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData/Local"))
        program_files = Path(os.getenv("ProgramFiles", "C:/Program Files"))
        candidates.extend([
            local / "Programs/Microsoft VS Code/Code.exe",
            program_files / "Microsoft VS Code/Code.exe",
            Path(os.getenv("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Microsoft VS Code/Code.exe",
        ])
        found = shutil.which("code.exe")
    else:
        found = shutil.which("code")
    if found:
        candidates.insert(0, Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def open_in_vscode(project_path=None):
    """Open a folder in VS Code without invoking a shell."""
    executable = find_vscode()
    if not executable:
        raise FileNotFoundError(
            "Não encontrei o VS Code. Instale o Visual Studio Code e habilite o comando code."
        )
    folder = Path(project_path or ROOT).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    return subprocess.Popen([executable, str(folder)], cwd=str(folder), shell=False)


def create_generated_project(name, files):
    """Validate and write an AI-generated file manifest into the safe workspace."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", str(name or "")):
        raise ValueError("Nome de projeto inválido.")
    if not isinstance(files, list) or not files or len(files) > _MAX_FILES:
        raise ValueError(f"O projeto deve conter de 1 a {_MAX_FILES} arquivos.")
    normalized = []
    total = 0
    seen = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "content"}:
            raise ValueError("Cada arquivo deve conter somente path e content.")
        relative = item["path"]
        content = item["content"]
        if not isinstance(relative, str) or not isinstance(content, str):
            raise ValueError("Caminho e conteúdo dos arquivos precisam ser texto.")
        rel = Path(relative)
        if rel.is_absolute() or not rel.parts or any(part in {"", ".", ".."} for part in rel.parts):
            raise ValueError("Caminho de arquivo inválido.")
        if rel.suffix.lower() in _BLOCKED_SUFFIXES:
            raise ValueError(f"Tipo de arquivo executável bloqueado: {rel.suffix}")
        normalized_path = rel.as_posix()
        if normalized_path in seen:
            raise ValueError("O manifesto contém caminhos duplicados.")
        seen.add(normalized_path)
        size = len(content.encode("utf-8"))
        if size > _MAX_FILE_BYTES:
            raise ValueError(f"Arquivo muito grande: {normalized_path}")
        total += size
        if total > _MAX_TOTAL_BYTES:
            raise ValueError("O projeto ultrapassa o limite total de 2 MB.")
        normalized.append((normalized_path, content))
    root = create_project(name)
    written = []
    for relative, content in normalized:
        written.append(write_project_file(name, relative, content))
    return root, tuple(written)


_TASKS = {
    "flutter_analyze": ("flutter", "analyze", "--no-pub"),
    "flutter_test": ("flutter", "test", "--no-pub"),
    "dart_analyze": ("dart", "analyze"),
    "python_compile": (sys.executable, "-m", "compileall", "-q", "."),
    "python_tests": (sys.executable, "-m", "unittest", "discover", "-s", "tests"),
}


def run_project_task(project_path, task, timeout=180):
    """Run one explicit, allowlisted validation task without a shell."""
    if task not in _TASKS and task != "python_run_main":
        raise ValueError("Tarefa de validação não permitida.")
    folder = Path(project_path).expanduser().resolve()
    workspace = ROOT.expanduser().resolve()
    if workspace not in folder.parents:
        raise ValueError("A validação só pode ser executada dentro da pasta de projetos do JARVIS.")
    if not folder.is_dir():
        raise FileNotFoundError("A pasta do projeto não existe.")

    if task == "python_run_main":
        # This is an explicit, confirmed run of the conventional entry point.
        # It is not an OS sandbox; do not run code the user does not trust.
        entrypoint = folder / "main.py"
        if not entrypoint.is_file():
            raise FileNotFoundError("Não encontrei main.py na pasta do projeto.")
        from python_environment import resolve_python_launcher, venv_interpreter_path
        project_python = venv_interpreter_path(folder)
        if project_python.is_file():
            command = [str(project_python), "-B", "main.py"]
        else:
            launcher = resolve_python_launcher()
            if not launcher:
                raise FileNotFoundError(
                    "Python 3 não foi encontrado. Instale Python 3 ou configure o .venv do projeto."
                )
            command = [*launcher, "-B", "main.py"]
        try:
            return subprocess.run(
                command, cwd=str(folder), shell=False, capture_output=True,
                text=True, errors="replace", timeout=min(max(int(timeout), 1), 30),
                check=False, stdin=subprocess.DEVNULL
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", "replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", "replace")
            return subprocess.CompletedProcess(
                command, 124, stdout,
                (stderr + "\nTempo limite de 30 segundos atingido; o processo foi interrompido.").strip()
            )

    command = list(_TASKS[task])
    if command[0] not in {sys.executable}:
        executable = shutil.which(command[0])
        if not executable:
            raise FileNotFoundError(
                f"{command[0]} não foi encontrado no PATH. Instale o SDK correspondente."
            )
        command[0] = executable
    return subprocess.run(
        command, cwd=str(folder), shell=False, capture_output=True,
        text=True, errors="replace", timeout=timeout, check=False
    )
