"""Safe project file workspace. Generated code is never executed automatically."""
from pathlib import Path
import re

ROOT=Path.home()/"Documents"/"JarvisProjects"

def _safe_project(name):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}",name or ""):
        raise ValueError("Nome de projeto inválido; use letras, números, _ ou -.")
    path=(ROOT/name).resolve()
    if ROOT.resolve() not in path.parents:
        raise ValueError("Caminho fora da área de projetos.")
    path.mkdir(parents=True,exist_ok=True)
    return path

def create_project(name):
    path=_safe_project(name)
    (path/"README.md").write_text("# "+name+"\n\nProjeto criado pelo JARVIS.\n",encoding="utf-8")
    return path

def write_project_file(name, relative_path, content):
    root=_safe_project(name)
    rel=Path(relative_path)
    if rel.is_absolute() or any(part in {"..",""} for part in rel.parts):
        raise ValueError("Caminho relativo inválido.")
    target=(root/rel).resolve()
    if root not in target.parents:
        raise ValueError("Tentativa de sair da pasta do projeto.")
    if len(content)>1_000_000:
        raise ValueError("Arquivo excede 1 MB nesta versão.")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(content,encoding="utf-8")
    return target
