"""Gera código longo em segundo plano.

Cada parte é gravada no arquivo assim que chega, então nada se perde se o programa fechar.
Dá para retomar depois com "continua o código". A porcentagem só existe quando o pedido tem
uma meta de linhas ("faz com 3 mil linhas").
"""
from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime
from pathlib import Path

from . import ia

MARCADOR_FIM = "FIM_DO_CODIGO"
TOKENS_POR_PARTE = 8192
TEMPO_MAXIMO_S = 72 * 3600
MAX_PARTES = 100_000
TRECHO_CONTEXTO = 3000
ALVO_MAXIMO = 1_000_000

PROMPT_SISTEMA = (
    "Você escreve código. "
    "Responda APENAS com o código, sem explicações, sem markdown e sem crases. "
    "Se o pedido for grande, escreva o código completo, sem resumir e sem usar reticências ou 'resto do código'. "
    "Quando o código estiver totalmente completo, escreva por último a linha FIM_DO_CODIGO. "
    "Nunca escreva essa linha antes do fim. "
    "Use Python, a não ser que o pedido diga outra linguagem. "
    "O código deve ser completo, legível e com comentários curtos em português."
)


def limpar_parte(texto: str) -> str:
    """Tira as cercas de markdown (```python) sem mexer nas bordas do texto."""
    return re.sub(r"```[a-zA-Z0-9+#]*\n?", "", texto)


def processar_resposta(texto: str) -> tuple[str, bool]:
    """Devolve (trecho sem o marcador, se o modelo declarou o fim)."""
    bruto = limpar_parte(texto)
    return bruto.replace(MARCADOR_FIM, ""), MARCADOR_FIM in bruto


def alvo_do_pedido(pedido: str) -> int:
    """Lê a meta de linhas do pedido. 0 quando não há meta."""
    m = re.search(r"(\d[\d.]*)\s*(mil\s+)?linhas", pedido.lower())
    if not m:
        return 0
    try:
        n = int(m.group(1).replace(".", ""))
    except ValueError:
        return 0
    total = n * 1000 if m.group(2) else n
    return min(total, ALVO_MAXIMO)


def porcentagem(linhas: int, alvo: int) -> int:
    return min(linhas * 100 // alvo, 100) if alvo > 0 else 0


def montar_mensagens(pedido: str, cauda: str, linhas: int, alvo: int) -> list[dict]:
    msgs = [
        {"role": "system", "content": PROMPT_SISTEMA},
        {"role": "user", "content": pedido},
    ]
    if cauda:
        # Manda só o fim do que já foi escrito, para não estourar o contexto do modelo.
        msgs.append({"role": "assistant", "content": cauda})
        falta = f" Ainda faltam {max(alvo - linhas, 0)} linhas." if alvo > 0 else ""
        msgs.append({
            "role": "user",
            "content": "Continue exatamente depois do trecho acima, sem repetir e sem explicar nada." + falta,
        })
    return msgs


class Gerador:
    def __init__(self, pasta: Path, chamar=None, tempo_maximo_s: int = TEMPO_MAXIMO_S):
        self.pasta = pasta
        self._chamar = chamar or ia.chamar
        self._tempo_maximo = tempo_maximo_s
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self.dados: dict = self._carregar()

    # ---- arquivos de apoio -------------------------------------------------

    def pasta_codigos(self) -> Path:
        return self.pasta / "codigos"

    def _estado_arq(self) -> Path:
        return self.pasta / "estado_codigo.json"

    def _carregar(self) -> dict:
        try:
            dados = json.loads(self._estado_arq().read_text(encoding="utf-8"))
            return dados if isinstance(dados, dict) else {}
        except (OSError, ValueError):
            return {}

    def _salvar(self) -> None:
        self.pasta.mkdir(parents=True, exist_ok=True)
        self._estado_arq().write_text(json.dumps(self.dados, ensure_ascii=False), encoding="utf-8")

    def _novo_arquivo(self) -> Path:
        pasta = self.pasta_codigos()
        pasta.mkdir(parents=True, exist_ok=True)
        base = "codigo_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        arq = pasta / (base + ".py")
        i = 1
        while arq.exists():
            arq = pasta / f"{base} ({i}).py"
            i += 1
        arq.touch()
        return arq

    # ---- API pública -------------------------------------------------------

    def em_andamento(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def iniciar(self, pedido: str | None = None) -> str:
        """Começa um código novo (pedido) ou retoma o último (pedido None)."""
        if self.em_andamento():
            return "Já estou gerando o código. Diga como está o código para ver o andamento."
        if not ia.configurado():
            return ("Configure a IA antes: defina JARVIS_IA_URL e JARVIS_IA_MODEL "
                    "(e JARVIS_IA_KEY, se o servidor pedir chave).")
        if pedido is not None:
            arq = self._novo_arquivo()
            self.dados = {
                "pedido": pedido,
                "arquivo": str(arq),
                "partes": 0,
                "linhas": 0,
                "alvo": alvo_do_pedido(pedido),
                "estado": "gerando",
            }
        else:
            if not self.dados.get("pedido"):
                return "Não há código para continuar."
            arq = Path(str(self.dados.get("arquivo", "")))
            if not arq.exists():
                return "Não encontrei o arquivo do código anterior."
            self.dados["estado"] = "gerando"
        self._salvar()
        self._parar.clear()
        self._thread = threading.Thread(target=self._gerar, args=(self.dados["pedido"], arq), daemon=True)
        self._thread.start()
        return "Comecei a gerar o código."

    def status(self) -> str:
        d = self.dados
        if not d.get("pedido"):
            return "Não há código sendo gerado."
        linhas = int(d.get("linhas", 0))
        alvo = int(d.get("alvo", 0))
        if self.em_andamento():
            estado = "sendo gerado"
        elif d.get("estado") == "gerando":
            estado = "interrompido. Diga continua o código para retomar"
        else:
            estado = str(d.get("estado", ""))
        meta = f" de {alvo} linhas, {porcentagem(linhas, alvo)} por cento" if alvo > 0 else ""
        return f"O código tem {linhas} linhas{meta}, e está {estado}."

    def parar(self) -> str:
        if not self.em_andamento():
            return "Não há geração em andamento."
        self._parar.set()
        return "Vou parar a geração. O que já foi escrito fica salvo."

    def listar(self) -> list[dict]:
        """Os códigos guardados, do mais novo para o mais antigo, com linhas e porcentagem."""
        atual = self.dados.get("arquivo")
        alvo_atual = int(self.dados.get("alvo", 0))
        concluido = self.dados.get("estado") == "concluido" and not self.em_andamento()
        pasta = self.pasta_codigos()
        if not pasta.is_dir():
            return []
        saida = []
        for f in sorted(pasta.glob("*.py"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                linhas = f.read_text(encoding="utf-8", errors="ignore").count("\n")
            except OSError:
                linhas = 0
            ehAtual = str(f) == atual
            alvo = alvo_atual if ehAtual else 0
            base_pronto = concluido if ehAtual else True
            pct = porcentagem(linhas, alvo) if alvo > 0 else (100 if base_pronto else -1)
            saida.append({
                "nome": f.name,
                "caminho": str(f),
                "linhas": linhas,
                "percentual": pct,
                "pronto": base_pronto and pct >= 100,
            })
        return saida

    # ---- trabalho em segundo plano ----------------------------------------

    def _gerar(self, pedido: str, arq: Path) -> None:
        inicio = time.monotonic()
        d = self.dados
        alvo = int(d.get("alvo", 0))
        partes = int(d.get("partes", 0))
        linhas = int(d.get("linhas", 0))
        try:
            cauda = arq.read_text(encoding="utf-8")[-TRECHO_CONTEXTO:]
        except OSError:
            cauda = ""
        estado = "concluido"
        vazias = 0
        try:
            while True:
                if self._parar.is_set():
                    estado = "parado"
                    break
                if time.monotonic() - inicio > self._tempo_maximo:
                    estado = "com o tempo esgotado"
                    break
                if partes >= MAX_PARTES:
                    estado = "no limite de partes"
                    break
                resposta = self._chamar(montar_mensagens(pedido, cauda, linhas, alvo), max_tokens=TOKENS_POR_PARTE)
                if resposta is None:
                    estado = "parado por erro na IA"
                    break
                parte, terminou = processar_resposta(resposta[0])
                if not parte.strip():
                    vazias += 1
                    if vazias >= 3:
                        estado = "parado por respostas vazias"
                        break
                    continue
                vazias = 0
                with arq.open("a", encoding="utf-8") as f:
                    f.write(parte)
                partes += 1
                linhas += parte.count("\n")
                cauda = (cauda + parte)[-TRECHO_CONTEXTO:]
                d.update(partes=partes, linhas=linhas)
                self._salvar()
                if alvo > 0 and linhas >= alvo:
                    break
                if alvo <= 0 and terminou:
                    break
        except OSError:
            estado = "parado por erro ao salvar"
        finally:
            d["estado"] = estado
            try:
                self._salvar()
            except OSError:
                pass
