"""Conversa com a IA configurada por você (servidor compatível com a API da OpenAI).

Nada de chave no código: a chave vem da variável de ambiente JARVIS_IA_KEY.
"""
from __future__ import annotations

import json
import os
import urllib.request


def _url() -> str:
    return os.environ.get("JARVIS_IA_URL", "").strip()


def configurado() -> bool:
    return _url().startswith(("http://", "https://"))


def chamar(mensagens: list[dict], max_tokens: int = 8192, timeout: int = 180) -> tuple[str, str] | None:
    """Devolve (texto, motivo_de_parada), ou None se a chamada falhar."""
    url = _url()
    if not url.startswith(("http://", "https://")):
        return None
    chave = os.environ.get("JARVIS_IA_KEY", "").strip()
    corpo = {
        "model": os.environ.get("JARVIS_IA_MODEL", "").strip(),
        "stream": False,
        "max_tokens": max_tokens,
        "messages": mensagens,
    }
    cabecalhos = {"Content-Type": "application/json"}
    if chave:
        cabecalhos["Authorization"] = "Bearer " + chave
    pedido = urllib.request.Request(
        url, data=json.dumps(corpo).encode("utf-8"), headers=cabecalhos, method="POST"
    )
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        escolha = dados["choices"][0]
        texto = escolha["message"].get("content") or ""
        return str(texto), str(escolha.get("finish_reason", "stop"))
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
        return None
