"""Gera projetos completos em segundo plano: vários arquivos, em uma ou mais linguagens.

O modelo escreve cada arquivo depois de um cabeçalho "=== ARQUIVO: caminho ===". O gerador
grava os arquivos na pasta do projeto, parte por parte. Erro de rede não para a geração:
ele espera e tenta de novo. Só para quando o modelo declara FIM_DO_PROJETO (com as linhas
pedidas), quando você manda parar, ou no limite de tempo.
"""
from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from . import ia

MARCADOR_FIM = "FIM_DO_PROJETO"
CABECALHO = re.compile(r"^=== ARQUIVO: (.+?) ===[ \t]*$", re.MULTILINE)
CERCA = re.compile(r"^```[a-zA-Z0-9+#.\-]*[ \t]*$\n?", re.MULTILINE)
TOKENS_POR_PARTE = 8192
MAX_PARTES = 100_000
TEMPO_MAXIMO_S = 72 * 3600
ALVO_MAXIMO = 1_000_000
TRECHO_CONTEXTO = 4000
ESPERAS_S = [5, 10, 20, 30, 60, 120, 300]
MAX_FALHAS = 200
OCIOSAS_PARA_PARAR = 4

PROMPT_SISTEMA = (
    "Você gera projetos de software completos e funcionando. Use quantos arquivos e quantas "
    "linguagens forem necessárias (HTML, CSS, JavaScript, Python, SQL, etc.). "
    "Antes de cada arquivo, escreva uma linha exatamente assim: === ARQUIVO: caminho/do/arquivo.ext === "
    "O caminho é relativo à pasta do projeto. Depois do cabeçalho, escreva o conteúdo COMPLETO do arquivo, "
    "sem markdown e sem crases. Nunca resuma e nunca use reticências ou 'resto do código'. "
    "Não pare no meio: escreva todos os arquivos que o projeto precisa, do começo ao fim. "
    "Quando o projeto estiver totalmente pronto, escreva por último a linha FIM_DO_PROJETO. "
    "Nunca escreva essa linha antes do fim."
)


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


def limpar_cercas(texto: str) -> str:
    """Tira linhas que são só cercas de markdown (```python), sem mexer no resto."""
    return CERCA.sub("", texto)


def extrair(texto: str) -> tuple[str, list[tuple[str, str]]]:
    """Separa o texto antes do primeiro cabeçalho e os blocos (caminho, conteúdo)."""
    cabecalhos = list(CABECALHO.finditer(texto))
    if not cabecalhos:
        return texto, []
    inicio = texto[: cabecalhos[0].start()]
    blocos = []
    for i, m in enumerate(cabecalhos):
        fim = cabecalhos[i + 1].start() if i + 1 < len(cabecalhos) else len(texto)
        conteudo = texto[m.end(): fim]
        if conteudo.startswith("\n"):
            conteudo = conteudo[1:]
        blocos.append((m.group(1).strip(), conteudo))
    return inicio, blocos


def caminho_seguro(projeto: Path, relativo: str) -> Path | None:
    """Monta o caminho dentro do projeto. Partes como '..' e 'C:' são descartadas."""
    partes = [p for p in relativo.replace("\\", "/").split("/")
              if p not in ("", ".", "..") and not p.endswith(":")]
    if not partes:
        return None
    return projeto.joinpath(*partes)


def _gravar(caminho: Path, texto: str, modo: str) -> int:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open(modo, encoding="utf-8") as f:
        f.write(texto)
    return texto.count("\n")


def _contar(pasta: Path) -> tuple[int, int]:
    """Devolve (número de arquivos, número de linhas) do projeto."""
    arquivos = linhas = 0
    if not pasta.is_dir():
        return 0, 0
    for f in pasta.rglob("*"):
        if f.is_file():
            arquivos += 1
            try:
                linhas += f.read_text(encoding="utf-8", errors="ignore").count("\n")
            except OSError:
                pass
    return arquivos, linhas


def montar_mensagens(pedido: str, cauda: str, linhas: int, alvo: int, arquivo_atual: str,
                     instrucao: str | None = None) -> list[dict]:
    msgs = [
        {"role": "system", "content": PROMPT_SISTEMA},
        {"role": "user", "content": pedido},
    ]
    if cauda:
        msgs.append({"role": "assistant", "content": cauda})
        partes = ["Continue exatamente depois do trecho acima, sem repetir e sem explicar nada."]
        if arquivo_atual:
            partes.append(f"Se o arquivo {arquivo_atual} ainda não terminou, continue-o; "
                          "senão comece o próximo arquivo com o cabeçalho.")
        if alvo > 0 and linhas < alvo:
            partes.append(f"Ainda faltam {alvo - linhas} linhas para o pedido.")
        if instrucao:
            partes.append(instrucao)
        msgs.append({"role": "user", "content": " ".join(partes)})
    return msgs


class Gerador:
    def __init__(self, pasta: Path, chamar=None, tempo_maximo_s: int = TEMPO_MAXIMO_S,
                 esperas: list[int] | None = None, max_falhas: int = MAX_FALHAS):
        self.pasta = pasta
        self._chamar = chamar or ia.chamar
        self._tempo_maximo = tempo_maximo_s
        self._esperas = ESPERAS_S if esperas is None else esperas
        self._max_falhas = max_falhas
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self.dados: dict = self._carregar()

    # ---- arquivos de apoio -------------------------------------------------

    def pasta_projetos(self) -> Path:
        return self.pasta / "projetos"

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

    def _salvar_seguro(self) -> None:
        try:
            self._salvar()
        except OSError:
            pass

    def _nova_pasta(self, pedido: str) -> Path:
        ascii_ = unicodedata.normalize("NFKD", pedido.lower()).encode("ascii", "ignore").decode()
        palavras = re.findall(r"[a-z0-9]+", ascii_)[:4]
        nome = datetime.now().strftime("%Y%m%d_%H%M%S") + ("_" + "-".join(palavras) if palavras else "")
        destino = self.pasta_projetos() / nome
        i = 1
        while destino.exists():
            destino = self.pasta_projetos() / f"{nome}_{i}"
            i += 1
        destino.mkdir(parents=True)
        return destino

    # ---- API pública -------------------------------------------------------

    def em_andamento(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def iniciar(self, pedido: str | None = None) -> str:
        """Começa um projeto novo (pedido) ou retoma o último (pedido None)."""
        if self.em_andamento():
            return "Já estou gerando o código. Diga como está o código para ver o andamento."
        if not ia.configurado():
            return ("Configure a IA antes, em Configurações ou no config.json (ia_url e ia_modelo).")
        if pedido is not None:
            projeto = self._nova_pasta(pedido)
            self.dados = {
                "pedido": pedido,
                "projeto": str(projeto),
                "arquivo_atual": "",
                "partes": 0,
                "linhas": 0,
                "alvo": alvo_do_pedido(pedido),
                "estado": "gerando",
            }
        else:
            if not self.dados.get("pedido"):
                return "Não há código para continuar."
            projeto = Path(str(self.dados.get("projeto", "")))
            if not projeto.is_dir():
                return "Não encontrei a pasta do projeto anterior."
            self.dados["estado"] = "gerando"
        self._salvar_seguro()
        self._parar.clear()
        self._thread = threading.Thread(target=self._gerar, args=(self.dados["pedido"], projeto), daemon=True)
        self._thread.start()
        return "Comecei a gerar o código."

    def status(self) -> str:
        d = self.dados
        if not d.get("pedido"):
            return "Não há código sendo gerado."
        arquivos, linhas = _contar(Path(str(d.get("projeto", ""))))
        alvo = int(d.get("alvo", 0))
        if self.em_andamento():
            estado = "tentando reconectar com a IA" if d.get("estado") == "reconectando" else "sendo gerado"
        elif d.get("estado") == "gerando":
            estado = "interrompido. Diga continua o código para retomar"
        else:
            estado = str(d.get("estado", ""))
        meta = f" de {alvo} linhas, {porcentagem(linhas, alvo)} por cento" if alvo > 0 else ""
        return f"O projeto tem {arquivos} arquivos e {linhas} linhas{meta}, e está {estado}."

    def parar(self) -> str:
        if not self.em_andamento():
            return "Não há geração em andamento."
        self._parar.set()
        return "Vou parar a geração. O que já foi escrito fica salvo."

    def listar(self) -> list[dict]:
        """Os projetos guardados, do mais novo para o mais antigo."""
        base = self.pasta_projetos()
        if not base.is_dir():
            return []
        atual = self.dados.get("projeto")
        alvo_atual = int(self.dados.get("alvo", 0))
        concluido = self.dados.get("estado") == "concluido" and not self.em_andamento()
        saida = []
        for pasta in sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True):
            arquivos, linhas = _contar(pasta)
            ehAtual = str(pasta) == atual
            alvo = alvo_atual if ehAtual else 0
            base_pronto = concluido if ehAtual else True
            pct = porcentagem(linhas, alvo) if alvo > 0 else (100 if base_pronto else -1)
            saida.append({
                "nome": pasta.name,
                "caminho": str(pasta),
                "arquivos": arquivos,
                "linhas": linhas,
                "percentual": pct,
                "pronto": base_pronto and pct >= 100,
            })
        return saida

    # ---- trabalho em segundo plano ----------------------------------------

    def _aplicar(self, projeto: Path, texto: str, atual: str) -> tuple[str, int]:
        """Grava o texto recebido nos arquivos certos. Devolve (arquivo atual, linhas novas)."""
        inicio, blocos = extrair(texto)
        novas = 0
        if inicio.strip():
            if not atual:
                atual = "codigo.txt"
            novas += _gravar(projeto / atual, inicio, "a")
        for relativo, conteudo in blocos:
            destino = caminho_seguro(projeto, relativo)
            if destino is None:
                continue
            modo = "a" if destino.exists() else "w"  # nunca apaga um arquivo que já existe
            novas += _gravar(destino, conteudo, modo)
            atual = destino.relative_to(projeto).as_posix()
        return atual, novas

    def _cauda(self, projeto: Path, atual: str) -> str:
        if not atual:
            return ""
        try:
            return (projeto / atual).read_text(encoding="utf-8", errors="ignore")[-TRECHO_CONTEXTO:]
        except OSError:
            return ""

    def _gerar(self, pedido: str, projeto: Path) -> None:
        inicio = time.monotonic()
        d = self.dados
        alvo = int(d.get("alvo", 0))
        linhas = int(d.get("linhas", 0))
        partes = int(d.get("partes", 0))
        atual = str(d.get("arquivo_atual", ""))
        cauda = self._cauda(projeto, atual)
        instrucao: str | None = None
        estado = "concluido"
        falhas = 0
        ociosas = 0
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
                resposta = self._chamar(montar_mensagens(pedido, cauda, linhas, alvo, atual, instrucao),
                                        max_tokens=TOKENS_POR_PARTE)
                instrucao = None
                if resposta is None:
                    # Erro de rede ou da IA: espera e tenta de novo, sem desistir do projeto.
                    falhas += 1
                    if falhas > self._max_falhas:
                        estado = "parado por erro na IA"
                        break
                    d["estado"] = "reconectando"
                    self._salvar_seguro()
                    espera = self._esperas[min(falhas - 1, len(self._esperas) - 1)] if self._esperas else 0
                    if self._parar.wait(espera):
                        estado = "parado"
                        break
                    continue
                falhas = 0
                d["estado"] = "gerando"
                texto = resposta[0]
                fim = MARCADOR_FIM in texto
                texto = limpar_cercas(texto).replace(MARCADOR_FIM, "")
                if not texto.strip():
                    ociosas += 1
                    if ociosas >= OCIOSAS_PARA_PARAR:
                        estado = "parado sem novidades"
                        break
                    continue
                atual, novas = self._aplicar(projeto, texto, atual)
                partes += 1
                linhas += novas
                cauda = (cauda + texto)[-TRECHO_CONTEXTO:]
                d.update(partes=partes, linhas=linhas, arquivo_atual=atual)
                self._salvar_seguro()
                ociosas = 0 if novas > 0 else ociosas + 1
                if fim and (alvo <= 0 or linhas >= alvo):
                    break
                if alvo > 0 and linhas >= alvo:
                    break
                if fim:
                    instrucao = (f"O projeto ainda tem {alvo - linhas} linhas a menos do que o pedido. "
                                 "Acrescente partes úteis e completas, sem repetir o que já existe.")
                if ociosas >= OCIOSAS_PARA_PARAR:
                    break
        except Exception as erro:  # o gerador não pode morrer em silêncio
            estado = f"parado por erro: {erro}"
        finally:
            d["estado"] = estado
            self._salvar_seguro()
