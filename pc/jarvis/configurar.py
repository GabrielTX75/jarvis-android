"""Assistente de configuração: pergunta no terminal e grava ~/JARVIS/config.json.

A chave e as senhas não aparecem enquanto você digita, e nunca são impressas.
Enter sem texto mantém o valor que já estava salvo.
"""
from __future__ import annotations

import getpass
import json

from . import config

PERGUNTAS = [
    ("ia_url", "Endereço completo da IA (ex.: https://api.groq.com/openai/v1/chat/completions)", False),
    ("ia_modelo", "Nome do modelo (ex.: llama-3.3-70b-versatile)", False),
    ("ia_chave", "Chave da IA (não aparece enquanto você digita)", True),
    ("busca_url", "Endereço do servidor de busca (Enter para pular)", False),
    ("busca_token", "Senha do servidor de busca (Enter para pular)", True),
]


def salvar_valores(novos: dict) -> str:
    """Grava os valores não vazios no config.json, mantendo o que já estava salvo."""
    dados = dict(config.ler_arquivo())
    for nome, valor in novos.items():
        if str(valor).strip():
            dados[nome] = str(valor).strip()
    arq = config.arquivo_config()
    arq.parent.mkdir(parents=True, exist_ok=True)
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(arq)


def configurar(perguntar=input, esconder=getpass.getpass) -> str:
    dados = config.ler_arquivo()
    novos = {}
    for nome, texto, secreto in PERGUNTAS:
        ja_tem = bool(str(dados.get(nome, "")).strip())
        dica = " [já salvo, Enter mantém]" if ja_tem else ""
        leitor = esconder if secreto else perguntar
        novos[nome] = leitor(texto + dica + ": ")
    arq = salvar_valores(novos)
    return f"Configuração salva em {arq}. Não mostrei os valores secretos."
