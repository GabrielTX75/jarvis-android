"""Núcleo do JARVIS: recebe o pedido, decide a ação e devolve a resposta."""
from __future__ import annotations

from collections import deque
from pathlib import Path

from . import ferramentas as f
from . import ia
from .busca import buscar
from .calc import calcular, formatar
from . import editor
from . import funcoes
from .codigo import Gerador
from .comandos import da_ia, prompt_sistema, reconhecer


class Nucleo:
    def __init__(self, pasta: Path | None = None, downloads: Path | None = None,
                 gerador: Gerador | None = None, aviso=print, abrir_editor: bool = True):
        self.pasta = pasta or f.pasta_dados()
        self.downloads = downloads or (Path.home() / "Downloads")
        self.gerador = gerador or Gerador(self.pasta)
        self.aviso = aviso
        self.abrir_editor = abrir_editor
        self._pendente: str | None = None
        # Últimas trocas com a IA, para ela entender o que foi dito antes.
        self.historico: deque[dict] = deque(maxlen=12)

    def processar(self, texto: str) -> tuple[str, bool]:
        """Devolve (resposta, se o JARVIS deve encerrar)."""
        acao = reconhecer(texto)
        if acao is None:
            if not ia.configurado():
                return ("Não entendi esse pedido. Exemplos: 'quanto é 25 por cento de 80', "
                        "'pesquisa receita de bolo', 'abre a calculadora'. "
                        "Para conversar livremente, configure a IA em ~/JARVIS/config.json.", False)
            mensagens = [{"role": "system", "content": prompt_sistema()}, *self.historico,
                         {"role": "user", "content": texto}]
            resposta = ia.chamar(mensagens, max_tokens=1024)
            if resposta is None:
                return ("Não consegui falar com a IA agora. Confira ia_url e ia_modelo em ~/JARVIS/config.json.", False)
            self.historico.append({"role": "user", "content": texto})
            self.historico.append({"role": "assistant", "content": resposta[0]})
            acao = da_ia(resposta[0])
            if acao is None:
                return (resposta[0].strip() or "Não tenho resposta para isso.", False)
        return self.executar(acao[0], acao[1], texto)

    def executar(self, nome: str, args: dict, texto: str = "") -> tuple[str, bool]:
        a = args or {}
        if nome not in ("desligar_pedido", "confirmar_desligar"):
            self._pendente = None
        if nome == "sair":
            return ("Até logo.", True)
        if nome == "copiar":
            return (funcoes.copiar(str(a.get("texto", ""))), False)
        if nome == "ler_area":
            return (funcoes.ler_area(), False)
        if nome == "abrir_site":
            return (funcoes.abrir_site(str(a.get("endereco", ""))), False)
        if nome == "abrir_pasta":
            return (funcoes.abrir_pasta(str(a.get("nome", ""))), False)
        if nome == "procurar_arquivo":
            return (funcoes.procurar_msg(str(a.get("termo", ""))), False)
        if nome == "info_sistema":
            return (funcoes.info_sistema(), False)
        if nome == "captura_tela":
            return (funcoes.captura_tela(self.pasta), False)
        if nome == "resumir_arquivo":
            return (funcoes.resumir_arquivo(str(a.get("nome", ""))), False)
        if nome == "desligar_pedido":
            self._pendente = "desligar"
            return ("Para desligar o computador em 1 minuto, diga: confirma desligar. "
                    "Para cancelar depois, diga: cancela o desligamento.", False)
        if nome == "confirmar_desligar":
            if self._pendente != "desligar":
                return ("Não há desligamento pedido. Diga: desliga o computador.", False)
            self._pendente = None
            return (funcoes.desligar_pc(), False)
        if nome == "cancelar_desligar":
            return (funcoes.cancelar_desligamento(), False)
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
            resposta = self.gerador.iniciar(str(a.get("pedido") or texto))
            if resposta.startswith("Comecei") and self.abrir_editor:
                problema = editor.abrir_no_vscode(Path(str(self.gerador.dados.get("projeto", ""))))
                if problema is None:
                    resposta += " Abri o arquivo no VS Code. O código vai aparecendo lá enquanto eu gero."
                else:
                    resposta += f" Não abri no VS Code: {problema}."
            return (resposta, False)
        if nome == "testar_codigo":
            if self.gerador.em_andamento():
                return ("O código ainda está sendo gerado. Espere terminar para testar.", False)
            arquivo = self.gerador.dados.get("projeto")
            if not arquivo:
                return ("Não há código para testar. Peça um código primeiro.", False)
            return (editor.testar_projeto(Path(str(arquivo))), False)
        if nome == "continuar_codigo":
            return (self.gerador.iniciar(None), False)
        if nome == "status_codigo":
            return (self.gerador.status(), False)
        if nome == "parar_codigo":
            return (self.gerador.parar(), False)
        if nome == "limpar_conversa":
            self.historico.clear()
            return ("Conversa esquecida. Podemos começar de novo.", False)
        if nome == "ler_tela":
            return ("Ler a tela não está disponível nesta versão para computador.", False)
        return ("Ainda não sei fazer isso.", False)
