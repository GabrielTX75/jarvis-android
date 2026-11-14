"""Funções do dia a dia no computador: área de transferência, sites, pastas, arquivos,
informações do sistema, print da tela, resumo de arquivos e desligar com confirmação."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from . import ia
from .ferramentas import pasta_dados
from .texto import normalizar

TIPOS_TEXTO = {".txt", ".md", ".py", ".csv", ".json", ".html", ".htm", ".css", ".js", ".xml", ".log"}
PASTAS_ATALHO = {
    "downloads": ("Downloads",),
    "documentos": ("Documents",),
    "area de trabalho": ("Desktop",),
    "desktop": ("Desktop",),
    "imagens": ("Pictures",),
    "musicas": ("Music",),
    "videos": ("Videos",),
}


def _sem_janela() -> dict:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


# ---- área de transferência -------------------------------------------------

def copiar(texto: str) -> str:
    texto = texto.strip()
    if not texto:
        return "Diga o que devo copiar."
    try:
        if os.name == "nt":
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
                           input=texto, text=True, encoding="utf-8", check=True, **_sem_janela())
        elif sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=texto, text=True, check=True)
        else:
            subprocess.run(["xclip", "-selection", "clipboard"], input=texto, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return "Não consegui copiar. No Linux, é preciso ter o xclip instalado."
    return "Copiado."


def ler_area() -> str:
    try:
        if os.name == "nt":
            r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                               capture_output=True, text=True, encoding="utf-8", **_sem_janela())
            conteudo = r.stdout
        elif sys.platform == "darwin":
            conteudo = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
        else:
            conteudo = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                      capture_output=True, text=True).stdout
    except OSError:
        return "Não consegui ler a área de transferência."
    conteudo = conteudo.strip()
    if not conteudo:
        return "A área de transferência está vazia."
    return "Está copiado: " + conteudo[:1000]


# ---- sites e pastas --------------------------------------------------------

def abrir_site(endereco: str) -> str:
    e = endereco.strip().lower().replace(" ", "")
    if not e:
        return "Diga o endereço do site."
    if not e.startswith(("http://", "https://")):
        e = "https://" + e
    host = urlparse(e).netloc
    if not host or "." not in host:
        return "Esse endereço não parece um site."
    webbrowser.open(e)
    return f"Abri {host}."


def _abrir_caminho(caminho: Path) -> None:
    if os.name == "nt":
        os.startfile(str(caminho))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(caminho)])
    else:
        subprocess.Popen(["xdg-open", str(caminho)])


def abrir_pasta(nome: str) -> str:
    nome = nome.strip()
    chave = normalizar(nome)
    if chave == "jarvis":
        alvo = pasta_dados()
    elif chave in PASTAS_ATALHO:
        alvo = Path.home().joinpath(*PASTAS_ATALHO[chave])
    else:
        alvo = Path.home() / nome
    if not alvo.is_dir():
        return f"Não encontrei a pasta {nome}."
    try:
        _abrir_caminho(alvo)
    except OSError:
        return "Não consegui abrir a pasta."
    return f"Abri a pasta {nome}."


# ---- arquivos --------------------------------------------------------------

def procurar_arquivo(termo: str, raizes: list[Path] | None = None, limite: int = 8,
                     profundidade: int = 4, max_visitados: int = 50_000) -> list[Path]:
    alvo = normalizar(termo).strip()
    if not alvo:
        return []
    raizes = raizes if raizes is not None else [Path.home() / "Documents", Path.home() / "Downloads",
                                                Path.home() / "Desktop"]
    achados: list[Path] = []
    visitados = 0
    for raiz in raizes:
        if not raiz.is_dir():
            continue
        for atual, dirs, arquivos in os.walk(raiz):
            if len(Path(atual).relative_to(raiz).parts) >= profundidade:
                dirs[:] = []
            for nome in arquivos:
                visitados += 1
                if alvo in normalizar(nome):
                    achados.append(Path(atual) / nome)
                if len(achados) >= limite or visitados > max_visitados:
                    return achados
    return achados


def procurar_msg(termo: str) -> str:
    achados = procurar_arquivo(termo)
    if not achados:
        return "Não encontrei arquivos com esse nome nas suas pastas principais."
    return "Encontrei: " + "; ".join(str(p) for p in achados)


def resumir_arquivo(nome: str, chamar=ia.chamar) -> str:
    achados = procurar_arquivo(nome, limite=1)
    if not achados:
        return f"Não encontrei o arquivo {nome}."
    arq = achados[0]
    if arq.suffix.lower() not in TIPOS_TEXTO:
        return f"Só consigo resumir arquivos de texto. {arq.name} não é um deles."
    if not ia.configurado():
        return "Configure a IA para eu conseguir resumir."
    texto = arq.read_text(encoding="utf-8", errors="replace")[:12000]
    resposta = chamar([
        {"role": "system", "content": "Resuma o texto a seguir em português, em poucos tópicos, sem inventar nada."},
        {"role": "user", "content": texto},
    ], max_tokens=800)
    if resposta is None:
        return "Não consegui falar com a IA agora."
    return f"Resumo de {arq.name}: " + resposta[0].strip()


# ---- sistema, print e desligamento ----------------------------------------

def info_sistema() -> str:
    partes = [f"Sistema: {platform.system()} {platform.release()}",
              f"Processador: {os.cpu_count()} núcleos"]
    try:
        import psutil  # opcional
    except ImportError:
        psutil = None
    if psutil is not None:
        try:
            mem = psutil.virtual_memory()
            partes.append(f"Memória: {mem.percent:.0f}% em uso de {mem.total / 1e9:.1f} GB")
        except Exception:
            pass
        try:
            bateria = psutil.sensors_battery()
            if bateria is not None:
                partes.append(f"Bateria: {bateria.percent:.0f}%"
                              + (" carregando" if bateria.power_plugged else " na bateria"))
        except Exception:
            pass
    else:
        partes.append("Memória e bateria: instale o psutil para ver.")
    uso = shutil.disk_usage(Path.home())
    partes.append(f"Disco: {uso.free / 1e9:.0f} GB livres de {uso.total / 1e9:.0f} GB")
    return ". ".join(partes) + "."


def captura_tela(pasta: Path) -> str:
    try:
        from PIL import ImageGrab  # opcional
    except ImportError:
        return "Para tirar print, instale o Pillow (pip install pillow)."
    try:
        imagem = ImageGrab.grab()
    except Exception:
        return "Não consegui tirar o print."
    destino = pasta / "capturas"
    destino.mkdir(parents=True, exist_ok=True)
    arq = destino / (datetime.now().strftime("print_%Y%m%d_%H%M%S") + ".png")
    imagem.save(arq)
    return f"Print salvo em {arq}."


def desligar_pc(minutos: int = 1) -> str:
    segundos = max(minutos, 1) * 60
    try:
        if os.name == "nt":
            subprocess.Popen(["shutdown", "/s", "/t", str(segundos)])
        else:
            subprocess.Popen(["shutdown", "-h", f"+{max(minutos, 1)}"])
    except OSError:
        return "Não consegui pedir o desligamento."
    return f"Vou desligar o computador em {minutos} minuto(s). Diga cancela o desligamento para parar."


def cancelar_desligamento() -> str:
    try:
        if os.name == "nt":
            subprocess.run(["shutdown", "/a"], check=True)
        else:
            subprocess.run(["shutdown", "-c"], check=True)
    except (OSError, subprocess.CalledProcessError):
        return "Não havia desligamento para cancelar."
    return "Desligamento cancelado."
