"""Configuração: variáveis de ambiente têm prioridade; depois vem o arquivo ~/JARVIS/config.json.

O arquivo fica no seu computador, fora do código. Nunca coloque chaves no repositório.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .ferramentas import pasta_dados

# nome curto -> variável de ambiente correspondente
VARIAVEIS = {
    "ia_url": "JARVIS_IA_URL",
    "ia_modelo": "JARVIS_IA_MODEL",
    "ia_chave": "JARVIS_IA_KEY",
    "busca_url": "JARVIS_BUSCA_URL",
    "busca_token": "JARVIS_BUSCA_TOKEN",
}


def arquivo_config() -> Path:
    return pasta_dados() / "config.json"


def _do_arquivo() -> dict:
    try:
        dados = json.loads(arquivo_config().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dados if isinstance(dados, dict) else {}


def valor(nome: str) -> str:
    """Devolve a configuração pelo nome curto (ex.: 'ia_url'), ou texto vazio."""
    do_ambiente = os.environ.get(VARIAVEIS[nome], "").strip()
    if do_ambiente:
        return do_ambiente
    bruto = _do_arquivo().get(nome)
    return str(bruto).strip() if bruto is not None else ""
