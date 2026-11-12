"""Pesquisa na web pelo seu servidor de busca (o mesmo Worker do app Android).

Configure com as variáveis JARVIS_BUSCA_URL (ex.: https://seu-worker.workers.dev) e JARVIS_BUSCA_TOKEN.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


def buscar(termo: str) -> str:
    base = os.environ.get("JARVIS_BUSCA_URL", "").strip().rstrip("/")
    token = os.environ.get("JARVIS_BUSCA_TOKEN", "").strip()
    if not base.startswith("https://") or not token:
        return "Configure as variáveis JARVIS_BUSCA_URL e JARVIS_BUSCA_TOKEN para pesquisar."
    if not termo.strip():
        return "Diga o que devo pesquisar."
    url = base + "/busca?q=" + urllib.parse.quote(termo.strip()[:200])
    pedido = urllib.request.Request(url, headers={"X-Jarvis-Token": token})
    try:
        with urllib.request.urlopen(pedido, timeout=25) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except (OSError, ValueError):
        return "Não consegui falar com o servidor de busca agora."
    lista = dados.get("resultados") if isinstance(dados, dict) else None
    if not lista:
        return "Não encontrei resultados para isso."
    partes = [
        f"{str(r.get('titulo', ''))[:120]}. {str(r.get('trecho', ''))[:160]}"
        for r in lista[:3] if isinstance(r, dict)
    ]
    return "Encontrei estes resultados. " + " ".join(partes)
