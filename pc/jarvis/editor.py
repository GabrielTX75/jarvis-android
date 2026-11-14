"""Abre o código no VS Code e testa o arquivo rodando-o com o Python.

Ao gerar código, o arquivo é gravado parte por parte. Como o VS Code recarrega
arquivos alterados no disco, o código vai aparecendo na tela enquanto é escrito.
"""
from __future__ import annotations

import os
import shutil
import webbrowser
import subprocess
import sys
from pathlib import Path

TEMPO_TESTE_S = 10
LIMITE_TEXTO = 3000


def _sem_janela() -> dict:
    # No Windows, o Python de teste não deve abrir uma janela de console própria.
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def abrir_no_vscode(arq: Path) -> str | None:
    """Abre o arquivo no VS Code. Devolve None se deu certo, ou o motivo em texto."""
    exe = shutil.which("code")
    if exe is None:
        return "o VS Code não foi encontrado (o comando 'code' não está no sistema)"
    try:
        subprocess.Popen([exe, str(arq)], **_sem_janela())
    except OSError:
        return "o sistema não conseguiu abrir o VS Code"
    return None


def interpretador_python() -> str | None:
    # Num .exe, sys.executable é o próprio JARVIS, então procura o Python instalado.
    if not getattr(sys, "frozen", False):
        return sys.executable
    return shutil.which("python") or shutil.which("py")


def checar_sintaxe(texto: str) -> str | None:
    try:
        compile(texto, "codigo.py", "exec")
    except SyntaxError as erro:
        return f"erro de sintaxe na linha {erro.lineno}: {erro.msg}"
    return None


def testar_arquivo(arq: Path, tempo: int = TEMPO_TESTE_S) -> str:
    """Roda o arquivo com o Python e devolve uma frase com o resultado."""
    if not arq.exists():
        return "Não encontrei o arquivo do código."
    texto = arq.read_text(encoding="utf-8", errors="replace")
    if not texto.strip():
        return "O arquivo do código está vazio."
    erro = checar_sintaxe(texto)
    if erro:
        return f"O código tem {erro}. Peça para o JARVIS corrigir."
    python = interpretador_python()
    if python is None:
        return "Não encontrei o Python para rodar o código. Instale o Python e tente de novo."
    try:
        resultado = subprocess.run(
            [python, "-X", "utf8", str(arq)],  # UTF-8 mesmo no Windows; -I ignoraria isso
            cwd=arq.parent,
            stdin=subprocess.DEVNULL,  # se o código pedir digitação, ele erra em vez de travar
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=tempo,
            **_sem_janela(),
        )
    except subprocess.TimeoutExpired:
        return (f"Rodou por {tempo} segundo(s) sem erro e eu parei o teste. "
                "Se for um programa que fica aberto (como um jogo), isso é normal.")
    except OSError as erro_so:
        return f"Não consegui rodar o código: {erro_so}"
    if resultado.returncode == 0:
        saida = resultado.stdout.strip()[:LIMITE_TEXTO]
        return "Rodou sem erros." + (f" Saída:\n{saida}" if saida else " Não mostrou nada na tela.")
    detalhe = (resultado.stderr.strip() or resultado.stdout.strip())[-LIMITE_TEXTO:]
    return f"Deu erro (código de saída {resultado.returncode}):\n{detalhe}"


def testar_projeto(pasta: Path) -> str:
    """Escolhe um jeito de rodar o projeto: main.py, index.html ou o primeiro .py."""
    if not pasta.is_dir():
        return "Não encontrei a pasta do projeto."
    if (pasta / "main.py").exists():
        return testar_arquivo(pasta / "main.py")
    if (pasta / "index.html").exists():
        webbrowser.open((pasta / "index.html").resolve().as_uri())
        return "Abri index.html no navegador. Confira se a página está do jeito que você pediu."
    scripts = sorted(pasta.rglob("*.py"))
    if scripts:
        return testar_arquivo(scripts[0])
    return ("Esse projeto não tem um jeito automático de rodar (main.py ou index.html). "
            "Abra a pasta no VS Code para rodar.")
