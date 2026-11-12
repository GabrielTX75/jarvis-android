"""Conversa com a IA configurada por você (servidor compatível com a API da OpenAI).

Endereço, modelo e chave ficam em ~/JARVIS/config.json (ou nas variáveis de ambiente).
O endereço precisa ser o completo, como .../v1/chat/completions.
"""
from __future__ import annotations

import json
import urllib.request

from . import config


def configurado() -> bool:
    return config.valor("ia_url").startswith(("http://", "https://"))


def chamar(mensagens: list[dict], max_tokens: int = 8192, timeout: int = 180) -> tuple[str, str] | None:
    """Devolve (texto, motivo_de_parada), ou None se a chamada falhar."""
    url = config.valor("ia_url")
    if not url.startswith(("http://", "https://")):
        return None
    chave = config.valor("ia_chave")
    corpo = {
        "model": config.valor("ia_modelo"),
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
