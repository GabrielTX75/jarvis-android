"""JARVIS Deploy: explicit, allowlisted APK builds and static-site publishing.

No API tokens are read or stored here. Remote publication relies on the user's
existing Netlify CLI or GitHub CLI login and is always confirmed by the UI.
"""
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from project_workspace import ROOT

_EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".dart_tool", ".netlify", ".vercel"}
_EXCLUDED_FILES = {".npmrc", ".netrc", ".pypirc", "id_rsa", "id_ed25519", "credentials.json", "service-account.json"}
_EXCLUDED_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore"}
_MAX_SITE_FILES = 5000
_MAX_SITE_BYTES = 100 * 1024 * 1024


def _project_folder(project_path):
    root = ROOT.expanduser().resolve()
    folder = Path(project_path).expanduser().resolve()
    if root not in folder.parents or not folder.is_dir():
        raise ValueError("O projeto precisa existir dentro da pasta de projetos do JARVIS.")
    return folder


def available_tools():
    """Report tool availability without installing anything or reading credentials."""
    return {
        "flutter": shutil.which("flutter") is not None,
        "gradle": shutil.which("gradle") is not None,
        "netlify": shutil.which("netlify") is not None,
        "gh": shutil.which("gh") is not None,
    }


def _run(command, cwd, timeout):
    return subprocess.run(
        command, cwd=str(cwd), shell=False, capture_output=True,
        text=True, errors="replace", timeout=timeout,
        check=False, stdin=subprocess.DEVNULL
    )


def build_apk(project_path, timeout=900):
    """Build a Flutter release APK or a native Android debug APK."""
    folder = _project_folder(project_path)
    flutter = shutil.which("flutter")
    gradle = shutil.which("gradle")

    if (folder / "pubspec.yaml").is_file():
        if not flutter:
            raise FileNotFoundError("Flutter SDK não encontrado no PATH. Instale-o manualmente; o JARVIS não instala SDKs.")
        command = [flutter, "build", "apk", "--release"]
        expected = folder / "build" / "app" / "outputs" / "flutter-apk" / "app-release.apk"
    elif (folder / "settings.gradle").is_file() or (folder / "settings.gradle.kts").is_file():
        if not gradle:
            raise FileNotFoundError("Gradle não encontrado no PATH. Instale-o manualmente; o JARVIS não instala SDKs.")
        command = [gradle, ":app:assembleDebug", "--no-daemon"]
        expected = folder / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    else:
        raise ValueError("Não reconheci um projeto Flutter (pubspec.yaml) ou Android Gradle (settings.gradle).")

    result = _run(command, folder, min(max(int(timeout), 60), 1800))
    if result.returncode != 0:
        return {"success": False, "returncode": result.returncode, "output": ((result.stdout or "") + "\n" + (result.stderr or ""))[-12000:], "apk": None}
    if not expected.is_file() or expected.stat().st_size <= 0:
        return {"success": False, "returncode": result.returncode, "output": "A compilação terminou, mas o APK esperado não foi encontrado. Verifique a saída do Gradle/Flutter.", "apk": None}
    return {"success": True, "returncode": 0, "output": ((result.stdout or "") + "\n" + (result.stderr or ""))[-12000:], "apk": str(expected)}


def _safe_site_files(folder):
    """Return only regular, in-workspace static files; omit common secrets and caches."""
    files = []
    total = 0
    for item in folder.rglob("*"):
        relative = item.relative_to(folder)
        if any(part in _EXCLUDED_DIRS for part in relative.parts):
            continue
        if item.is_symlink() or not item.is_file():
            continue
        name = item.name.lower()
        if name in _EXCLUDED_FILES or name.startswith(".env") or item.suffix.lower() in _EXCLUDED_SUFFIXES:
            continue
        resolved = item.resolve()
        if folder not in resolved.parents:
            continue
        total += item.stat().st_size
        files.append(item)
        if len(files) > _MAX_SITE_FILES or total > _MAX_SITE_BYTES:
            raise ValueError("O site excede o limite de 5.000 arquivos ou 100 MB.")
    return files


def package_static_site(project_path, output_path=None):
    """Create a ZIP of a ready-to-publish static site; never runs build scripts."""
    folder = _project_folder(project_path)
    if not (folder / "index.html").is_file():
        raise ValueError("Site estático precisa ter index.html na raiz. Projetos React/Vite precisam ser compilados antes.")
    destination = Path(output_path).expanduser().resolve() if output_path else folder.parent / (folder.name + "-site.zip")
    if destination == folder or folder in destination.parents:
        raise ValueError("O ZIP de saída não pode ficar dentro da pasta do projeto.")
    files = _safe_site_files(folder)
    if not any(item.name.lower() == "index.html" and item.parent == folder for item in files):
        raise ValueError("O index.html não passou pela validação de publicação.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in files:
            archive.write(item, item.relative_to(folder).as_posix())
    return destination


def publish_static_site(project_path, timeout=300):
    """Publish sanitized static files with the user's Netlify CLI login."""
    folder = _project_folder(project_path)
    if not (folder / "index.html").is_file():
        raise ValueError("Não encontrei index.html na raiz do site.")
    netlify = shutil.which("netlify")
    if not netlify:
        raise FileNotFoundError("Netlify CLI não encontrado. Instale e autentique-se manualmente; o JARVIS não solicita nem armazena tokens.")
    files = _safe_site_files(folder)
    if not any(item.name.lower() == "index.html" and item.parent == folder for item in files):
        raise ValueError("O index.html não passou pela validação de publicação.")
    with tempfile.TemporaryDirectory(prefix="jarvis-site-") as staging:
        stage = Path(staging)
        for item in files:
            target = stage / item.relative_to(folder)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
        result = _run([netlify, "deploy", "--prod", "--dir", str(stage), "--json"], folder, min(max(int(timeout), 30), 600))
    output = ((result.stdout or "") + "\n" + (result.stderr or ""))[-12000:]
    if result.returncode != 0:
        return {"success": False, "returncode": result.returncode, "output": output, "url": None}
    match = re.search(r'"(url|deploy_url|ssl_url)"\s*:\s*"(https://[^"]+)"', result.stdout or "")
    url = match.group(2) if match else None
    return {"success": True, "returncode": 0, "output": output, "url": url}


def publish_apk_release(project_path, apk_path, timeout=180):
    """Upload a built APK as a new GitHub Release using the user's gh login."""
    folder = _project_folder(project_path)
    apk = Path(apk_path).expanduser().resolve()
    if not apk.is_file() or apk.suffix.lower() != ".apk" or apk.stat().st_size <= 0:
        raise ValueError("O arquivo APK não existe ou é inválido.")
    gh = shutil.which("gh")
    if not gh:
        raise FileNotFoundError("GitHub CLI (gh) não encontrado. Instale e autentique-se manualmente.")
    status = _run([gh, "auth", "status"], folder, 20)
    if status.returncode != 0:
        raise PermissionError("GitHub CLI não está autenticado. Faça login manualmente com gh auth login.")
    repo = _run([gh, "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"], folder, 20)
    if repo.returncode != 0 or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\s*", repo.stdout or ""):
        raise RuntimeError("Não consegui identificar um repositório. Execute 'gh repo set-default DONO/REPOSITORIO' uma vez e tente novamente.")
    tag = "jarvis-apk-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    command = [gh, "release", "create", tag, str(apk), "--title", "JARVIS APK " + tag, "--notes", "APK compilado pelo JARVIS Deploy."]
    result = _run(command, folder, min(max(int(timeout), 30), 600))
    output = ((result.stdout or "") + "\n" + (result.stderr or ""))[-12000:]
    if result.returncode != 0:
        return {"success": False, "returncode": result.returncode, "output": output, "release": None}
    match = re.search(r"https://github\.com/[^\s]+/releases/tag/[^\s]+", output)
    return {"success": True, "returncode": 0, "output": output, "release": match.group(0) if match else None}
