"""Entende o pedido. Primeiro tenta regras simples; se não reconhecer, a IA pode responder em JSON."""
from __future__ import annotations

import json
import re

from .calc import calcular
from .texto import normalizar

Acao = tuple[str, dict]

# Nome da ação -> o que ela recebe em "args" (usado no prompt da IA).
ACOES_DISPONIVEIS = {
    "pesquisar": "termo",
    "calcular": "expressao",
    "abrir_app": "consulta (nome do programa)",
    "anotar": "texto",
    "ler_anotacoes": "",
    "apagar_anotacoes": "",
    "lembrete": "segundos (número), texto",
    "tocar_musica": "termo",
    "hora": "",
    "data": "",
    "organizar_downloads": "",
    "desfazer_organizacao": "",
    "gerar_codigo": "pedido",
    "continuar_codigo": "",
    "status_codigo": "",
    "parar_codigo": "",
    "ler_tela": "",
    "limpar_conversa": "",
}


def _limpo(texto: str) -> str:
    t = normalizar(texto)
    t = re.sub(r"[?!.,;:]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def reconhecer(texto: str) -> Acao | None:
    """Devolve (ação, argumentos) ou None se nenhuma regra servir."""
    original = texto.strip()
    t = _limpo(original)
    if not t:
        return None

    if t in {"sair", "tchau", "encerrar", "ate logo", "fechar jarvis"}:
        return ("sair", {})

    # Gerar código vem primeiro: "faz um código que continua..." não deve virar "continuar".
    if re.match(r"^(gera|gere|cria|crie|escreve|escreva|faz|faca|fazer|monta|monte)\b", t) and "codigo" in t:
        return ("gerar_codigo", {"pedido": original})
    if re.search(r"\b(continua|continue|retoma|retome)\b.*\bcodigo\b", t):
        return ("continuar_codigo", {})
    if re.search(r"\b(como esta|status|andamento)\b.*\bcodigo\b|\bcodigo\b.*\b(como esta|andamento|status)\b", t):
        return ("status_codigo", {})
    if re.search(r"\b(para|pare|parar|cancela|cancele)\b.*\bcodigo\b", t):
        return ("parar_codigo", {})

    m = re.match(r"^(?:pesquis\w*|procur\w*|busc\w*)\s+(?:na (?:internet|web)\s+|no google\s+|sobre\s+)?(?P<termo>.+)$", t)
    if m:
        return ("pesquisar", {"termo": m["termo"]})

    m = re.search(
        r"\b(?:me lembra|me lembre|lembrete|lembra me|lembre me|lembrar)\b.*?\b(?:em|daqui a)\s+"
        r"(\d+)\s*(segundo|segundos|minuto|minutos|hora|horas)\b\s*(?:de|para|que|sobre)?\s*(?P<texto>.*)$",
        t,
    )
    if m:
        unidade = m[2]
        fator = 3600 if unidade.startswith("hora") else 60 if unidade.startswith("minuto") else 1
        return ("lembrete", {"segundos": int(m[1]) * fator, "texto": m["texto"].strip()})

    m = re.match(r"^(?:anota|anote|anotar)\s+(?:que\s+)?(?P<texto>.+)$", t)
    if m:
        return ("anotar", {"texto": m["texto"]})
    if re.search(r"\b(apag\w*|limp\w*|exclu\w*)\b.*\banotac\w*", t):
        return ("apagar_anotacoes", {})
    if re.search(r"\banotac\w*\b", t) and re.search(r"\b(le|ler|leia|lista|liste|mostra|mostre|quais|minhas)\b", t):
        return ("ler_anotacoes", {})

    m = re.match(
        r"^(?:toca|toque|tocar|coloca|coloque|poe|bota|bote)\s+"
        r"(?:a musica |uma musica |musica |a |o |uma |um )?(?P<termo>.+)$",
        t,
    )
    if m:
        return ("tocar_musica", {"termo": m["termo"]})

    if re.search(r"\b(desfaz\w*)\b.*\borganiz", t):
        return ("desfazer_organizacao", {})
    if re.search(r"\borganiz\w*\b.*\b(downloads?|arquivos)\b", t):
        return ("organizar_downloads", {})

    if re.search(r"\bque horas\b|\bqual (?:e |eh )?(?:a )?hora\b|\bhoras sao\b", t):
        return ("hora", {})
    if re.search(r"\bqual (?:e |eh )?(?:a )?data\b|\bdata de hoje\b|\bque dia (?:e |eh )?hoje\b", t):
        return ("data", {})

    if re.search(r"\b(esquece|esqueca|limpa|limpe|apaga|apague|zera|zere)\b.*\bconversa\b", t):
        return ("limpar_conversa", {})

    if re.search(r"\b(le|leia|ler)\b.*\btela\b", t):
        return ("ler_tela", {})

    m = re.match(r"^(?:quanto (?:e|da|eh)|calcula|calcule|calcular|conta)\s+(?P<e>.+)$", t)
    if m and calcular(m["e"]) is not None:
        return ("calcular", {"expressao": m["e"]})
    if (re.search(r"\d", t)
            and re.search(r"[+*/^]|\b(mais|menos|vezes|dividido|raiz|elevado|por cento)\b|\d\s*x\s*\d", t)
            and calcular(t) is not None):
        return ("calcular", {"expressao": t})

    m = re.match(r"^(?:abre|abra|abrir|inicia|iniciar|executa|executar)\s+(?:o |a |os |as )?(?:app |aplicativo |programa )?(?P<consulta>.+)$", t)
    if m:
        return ("abrir_app", {"consulta": m["consulta"]})

    return None


def da_ia(texto: str) -> Acao | None:
    """Lê a resposta da IA. Só aceita JSON com uma ação conhecida; qualquer outra coisa é texto."""
    s = texto.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?|```$", "", s).strip()
    if not s.startswith("{"):
        return None
    try:
        dados = json.loads(s)
    except ValueError:
        return None
    if not isinstance(dados, dict):
        return None
    nome = dados.get("acao")
    args = dados.get("args") or {}
    if nome not in ACOES_DISPONIVEIS or not isinstance(args, dict):
        return None
    return (nome, args)


def prompt_sistema() -> str:
    catalogo = "; ".join(
        f"{nome} ({desc})" if desc else nome for nome, desc in ACOES_DISPONIVEIS.items()
    )
    return (
        "Você é o JARVIS, assistente de um computador. Responda em português, de forma curta. "
        "Se o pedido exigir uma ação, responda SOMENTE com JSON no formato "
        '{"acao": "nome", "args": {...}}. '
        f"Ações disponíveis: {catalogo}. "
        "Se não for uma ação, responda em texto normal."
    )
