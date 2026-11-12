"""Núcleo do JARVIS: recebe o pedido, decide a ação e devolve a resposta."""
from __future__ import annotations

from pathlib import Path

from . import ferramentas as f
from . import ia
from .busca import buscar
from .calc import calcular, formatar
from .codigo import Gerador
from .comandos import da_ia, prompt_sistema, reconhecer


class Nucleo:
    def __init__(self, pasta: Path | None = None, downloads: Path | None = None,
                 gerador: Gerador | None = None, aviso=print):
        self.pasta = pasta or f.pasta_dados()
        self.downloads = downloads or (Path.home() / "Downloads")
        self.gerador = gerador or Gerador(self.pasta)
        self.aviso = aviso

    def processar(self, texto: str) -> tuple[str, bool]:
        """Devolve (resposta, se o JARVIS deve encerrar)."""
        acao = reconhecer(texto)
        if acao is None:
            if not ia.configurado():
                return ("Não entendi esse pedido. Exemplos: 'quanto é 25 por cento de 80', "
                        "'pesquisa receita de bolo', 'abre a calculadora'. "
                        "Para conversar livremente, configure JARVIS_IA_URL.", False)
            resposta = ia.chamar(
                [{"role": "system", "content": prompt_sistema()}, {"role": "user", "content": texto}],
                max_tokens=1024,
            )
            if resposta is None:
                return ("Não consegui falar com a IA agora.", False)
            acao = da_ia(resposta[0])
            if acao is None:
                return (resposta[0].strip() or "Não tenho resposta para isso.", False)
        return self.executar(acao[0], acao[1], texto)

    def executar(self, nome: str, args: dict, texto: str = "") -> tuple[str, bool]:
        a = args or {}
        if nome == "sair":
            return ("Até logo.", True)
        if nome == "pesquisar":
            return (buscar(str(a.get("termo", ""))), False)
        if nome == "calcular":
            valor = calcular(str(a.get("expressao", "")))
            return ((formatar(valor) + ".") if valor is not None else "Não consegui calcular isso.", False)
        if nome == "abrir_app":
            return (f.abrir_app(str(a.get("consulta", ""))), False)
        if nome == "anotar":
            return (f.anotar(self.pasta, str(a.get("texto", ""))), False)
        if nome == "ler_anotacoes":
            return (f.ler_anotacoes(self.pasta), False)
        if nome == "apagar_anotacoes":
            return (f.apagar_anotacoes(self.pasta), False)
        if nome == "lembrete":
            try:
                segundos = int(a.get("segundos", 0))
            except (TypeError, ValueError):
                return ("Não entendi o tempo do lembrete.", False)
            return (f.lembrete(segundos, str(a.get("texto", "")) or "tempo acabou", self.aviso), False)
        if nome == "tocar_musica":
            return (f.tocar_musica(str(a.get("termo", ""))), False)
        if nome == "hora":
            return (f.hora_agora(), False)
        if nome == "data":
            return (f.data_hoje(), False)
        if nome == "organizar_downloads":
            return (f.organizar_downloads(self.downloads, self.pasta), False)
        if nome == "desfazer_organizacao":
            return (f.desfazer_organizacao(self.pasta), False)
        if nome == "gerar_codigo":
            return (self.gerador.iniciar(str(a.get("pedido") or texto)), False)
        if nome == "continuar_codigo":
            return (self.gerador.iniciar(None), False)
        if nome == "status_codigo":
            return (self.gerador.status(), False)
        if nome == "parar_codigo":
            return (self.gerador.parar(), False)
        if nome == "ler_tela":
            return ("Ler a tela não está disponível nesta versão para computador.", False)
        return ("Ainda não sei fazer isso.", False)
