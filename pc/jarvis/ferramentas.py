"""Ferramentas do dia a dia: anotações, lembretes, programas, música e a pasta Downloads."""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from .texto import normalizar

CATEGORIAS = {
    "Imagens": {"jpg", "jpeg", "png", "gif", "webp", "heic", "bmp"},
    "Videos": {"mp4", "mkv", "mov", "avi", "3gp", "webm"},
    "Audios": {"mp3", "wav", "ogg", "m4a", "opus", "aac", "flac"},
    "Documentos": {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "odt", "rtf"},
    "Instaladores": {"exe", "msi", "apk", "dmg", "deb"},
    "Compactados": {"zip", "rar", "7z", "tar", "gz"},
}

ANOTACOES = "anotacoes.json"
ORGANIZACAO = "organizacao.json"


def pasta_dados() -> Path:
    """Onde o JARVIS guarda anotações, códigos e o registro da organização. Pode ser trocada por JARVIS_PASTA."""
    return Path(os.environ.get("JARVIS_PASTA") or (Path.home() / "JARVIS"))


def _ler_lista(arq: Path) -> list:
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return dados if isinstance(dados, list) else []


def _gravar(arq: Path, dados) -> None:
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


# ---- anotações ---------------------------------------------------------------

def anotar(pasta: Path, texto: str) -> str:
    texto = texto.strip()
    if not texto:
        return "Diga o que devo anotar."
    lista = _ler_lista(pasta / ANOTACOES)
    lista.append({"quando": datetime.now().isoformat(timespec="minutes"), "texto": texto})
    _gravar(pasta / ANOTACOES, lista)
    return f"Anotado: {texto}"


def ler_anotacoes(pasta: Path) -> str:
    textos = [str(a.get("texto", "")) for a in _ler_lista(pasta / ANOTACOES) if isinstance(a, dict)]
    if not textos:
        return "Você não tem anotações."
    return f"Você tem {len(textos)} anotações. As últimas são: " + "; ".join(textos[-5:]) + "."


def apagar_anotacoes(pasta: Path) -> str:
    arq = pasta / ANOTACOES
    if not arq.exists():
        return "Não havia anotações."
    try:
        arq.unlink()
    except OSError:
        return "Não consegui apagar as anotações."
    return "Apaguei as anotações."


# ---- lembretes ---------------------------------------------------------------

def _duracao(segundos: int) -> str:
    if segundos >= 3600 and segundos % 3600 == 0:
        return f"{segundos // 3600} hora(s)"
    if segundos >= 60 and segundos % 60 == 0:
        return f"{segundos // 60} minuto(s)"
    return f"{segundos} segundo(s)"


def lembrete(segundos: int, texto: str, aviso=print) -> str:
    """Agenda um aviso. Ele só dispara enquanto o JARVIS estiver aberto."""
    if segundos <= 0:
        return "Diga um tempo maior que zero."
    t = threading.Timer(segundos, aviso, args=(f"Lembrete: {texto}",))
    t.daemon = True
    t.start()
    return f"Vou te lembrar em {_duracao(segundos)}."


# ---- abrir programas ---------------------------------------------------------

def _ler_desktop(caminho: Path) -> tuple[str | None, str | None]:
    nome = comando = None
    try:
        linhas = caminho.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None, None
    for linha in linhas:
        if linha.startswith("Name=") and nome is None:
            nome = linha[5:].strip()
        elif linha.startswith("Exec=") and comando is None:
            comando = re.sub(r"\s%[a-zA-Z]", "", linha[5:]).strip()
    return nome, comando


def _candidatos() -> dict[str, str]:
    """Nome normalizado -> o que abrir (atalho, app ou comando), conforme o sistema."""
    achados: dict[str, str] = {}
    if sys.platform == "win32":
        raizes = [os.environ.get("APPDATA", ""), os.environ.get("ProgramData", "")]
        for raiz in raizes:
            pasta = Path(raiz) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            if raiz and pasta.is_dir():
                for atalho in pasta.rglob("*.lnk"):
                    achados.setdefault(normalizar(atalho.stem), str(atalho))
    elif sys.platform == "darwin":
        for app in Path("/Applications").glob("*.app"):
            achados.setdefault(normalizar(app.stem), str(app))
    else:
        for pasta in [Path("/usr/share/applications"), Path.home() / ".local/share/applications"]:
            if pasta.is_dir():
                for desktop in pasta.glob("*.desktop"):
                    nome, comando = _ler_desktop(desktop)
                    if nome and comando:
                        achados.setdefault(normalizar(nome), comando)
    return achados


def casar(consulta: str, candidatos: dict[str, str]) -> str | None:
    """Acha o programa pelo nome exato ou por um trecho do nome."""
    procurado = normalizar(consulta)
    if not procurado:
        return None
    if procurado in candidatos:
        return candidatos[procurado]
    for nome in sorted(candidatos, key=len):
        if procurado in nome:
            return candidatos[nome]
    return None


def abrir_app(consulta: str) -> str:
    consulta = consulta.strip()
    if not consulta:
        return "Diga qual programa devo abrir."
    alvo = casar(consulta, _candidatos()) or shutil.which(consulta)
    if alvo is None:
        return f"Não encontrei nenhum programa chamado {consulta}."
    try:
        if sys.platform == "win32":
            os.startfile(alvo)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", alvo])
        else:
            subprocess.Popen(shlex.split(alvo), start_new_session=True)
    except (OSError, ValueError):
        return "Não consegui abrir esse programa."
    return f"Abri {consulta}."


# ---- música, data e hora -----------------------------------------------------

def tocar_musica(termo: str) -> str:
    """Abre a busca no YouTube no navegador. Não toca direto, para não depender de conta ou API."""
    termo = termo.strip()
    if not termo:
        return "Diga qual música devo tocar."
    webbrowser.open("https://www.youtube.com/results?search_query=" + quote_plus(termo))
    return f"Abri a busca de {termo} no YouTube. Escolha a música e dê play."


def hora_agora() -> str:
    return f"São {datetime.now():%H:%M}."


def data_hoje() -> str:
    return f"Hoje é {datetime.now():%d/%m/%Y}."


# ---- organizar a pasta Downloads ---------------------------------------------

def _destino_sem_repetir(pasta: Path, nome: str) -> Path:
    destino = pasta / nome
    base, ext = Path(nome).stem, Path(nome).suffix
    i = 1
    while destino.exists():
        destino = pasta / f"{base} ({i}){ext}"
        i += 1
    return destino


def organizar_downloads(downloads: Path, pasta: Path) -> str:
    """Move os arquivos soltos para pastas por tipo. Nunca apaga; guarda o registro para desfazer."""
    if not downloads.is_dir():
        return "Não encontrei a pasta Downloads."
    movimentos: list[dict] = []
    usadas: set[str] = set()
    for arq in sorted(p for p in downloads.iterdir() if p.is_file()):
        ext = arq.suffix.lower().lstrip(".")
        categoria = next((nome for nome, exts in CATEGORIAS.items() if ext in exts), "Outros")
        dir_destino = downloads / categoria
        dir_destino.mkdir(exist_ok=True)
        destino = _destino_sem_repetir(dir_destino, arq.name)
        try:
            arq.rename(destino)
        except OSError:
            continue
        movimentos.append({"de": str(arq), "para": str(destino)})
        usadas.add(categoria)
    if not movimentos:
        return "Não encontrei arquivos soltos na pasta Downloads."
    pasta.mkdir(parents=True, exist_ok=True)
    _gravar(pasta / ORGANIZACAO, movimentos)
    return (f"Organizei {len(movimentos)} arquivos em {len(usadas)} pastas. "
            "Diga desfazer organização para voltar como estava.")


def desfazer_organizacao(pasta: Path) -> str:
    arq = pasta / ORGANIZACAO
    if not arq.exists():
        return "Não há organização para desfazer."
    try:
        movimentos = json.loads(arq.read_text(encoding="utf-8"))
        voltaram = 0
        for m in reversed(movimentos):
            para, de = Path(m["para"]), Path(m["de"])
            if para.exists() and not de.exists():
                para.rename(de)
                voltaram += 1
    except (OSError, ValueError, KeyError, TypeError):
        return "O registro da organização está corrompido ou algum arquivo não pôde voltar."
    arq.unlink(missing_ok=True)
    return f"Desfiz a organização. {voltaram} arquivos voltaram para Downloads."
