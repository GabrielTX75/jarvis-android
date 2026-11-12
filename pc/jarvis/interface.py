"""Janela do JARVIS para computador. Usa tkinter, que já vem com o Python."""
from __future__ import annotations

import queue
import threading
import tkinter as tk

from . import config
from .configurar import PERGUNTAS, salvar_valores
from .nucleo import Nucleo

COR_FUNDO = "#0f172a"
COR_CAMPO = "#1e293b"
COR_TEXTO = "#e2e8f0"
COR_VOCE = "#38bdf8"
COR_JARVIS = "#a7f3d0"
COR_AVISO = "#fde68a"
INTERVALO_MS = 150


class Janela:
    def __init__(self, raiz: tk.Tk, nucleo: Nucleo | None = None):
        self.raiz = raiz
        self.fila: queue.Queue = queue.Queue()
        self.nucleo = nucleo or Nucleo(aviso=lambda m: self.fila.put(("aviso", m)))
        self.ocupado = False

        raiz.title("JARVIS")
        raiz.geometry("760x560")
        raiz.minsize(480, 360)
        raiz.configure(bg=COR_FUNDO)

        topo = tk.Frame(raiz, bg=COR_FUNDO)
        topo.pack(side="top", fill="x", padx=12, pady=(10, 0))
        tk.Label(topo, text="JARVIS", fg=COR_JARVIS, bg=COR_FUNDO,
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Button(topo, text="Configurações", command=self.abrir_configuracoes).pack(side="right")

        base = tk.Frame(raiz, bg=COR_FUNDO)
        base.pack(side="bottom", fill="x", padx=12, pady=12)
        self.campo = tk.Entry(base, bg=COR_CAMPO, fg=COR_TEXTO, insertbackground=COR_TEXTO,
                              relief="flat", font=("Segoe UI", 11))
        self.campo.pack(side="left", fill="x", expand=True, ipady=6)
        self.campo.bind("<Return>", lambda evento: self.enviar())
        self.botao = tk.Button(base, text="Enviar", command=self.enviar)
        self.botao.pack(side="right", padx=(8, 0))

        meio = tk.Frame(raiz, bg=COR_FUNDO)
        meio.pack(side="top", fill="both", expand=True, padx=12, pady=10)
        barra = tk.Scrollbar(meio)
        barra.pack(side="right", fill="y")
        self.log = tk.Text(meio, wrap="word", bg=COR_FUNDO, fg=COR_TEXTO, relief="flat",
                           padx=10, pady=8, font=("Segoe UI", 11), state="disabled",
                           yscrollcommand=barra.set)
        self.log.pack(side="left", fill="both", expand=True)
        barra.configure(command=self.log.yview)
        self.log.tag_configure("voce", foreground=COR_VOCE, font=("Segoe UI", 11, "bold"))
        self.log.tag_configure("jarvis", foreground=COR_JARVIS)
        self.log.tag_configure("aviso", foreground=COR_AVISO)

        if not config.valor("ia_url"):
            self.escrever("JARVIS", "A IA ainda não está configurada. Clique em Configurações "
                                    "e informe o endereço, o modelo e a chave.", "aviso")
        self.escrever("JARVIS", "Pronto. Digite um pedido, por exemplo: quanto é 25 por cento de 80.", "jarvis")
        self.raiz.after(INTERVALO_MS, self._checar_fila)

    # ---- escrita no histórico ----------------------------------------------

    def escrever(self, quem: str, texto: str, tag: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", quem + ": ", "voce" if quem == "Você" else tag)
        self.log.insert("end", texto + "\n", tag)
        self.log.configure(state="disabled")
        self.log.see("end")

    # ---- envio de pedidos ----------------------------------------------------

    def enviar(self) -> None:
        texto = self.campo.get().strip()
        if not texto or self.ocupado:
            return
        self.campo.delete(0, "end")
        self.escrever("Você", texto, "voce")
        self._ocupar(True)
        threading.Thread(target=self._trabalhar, args=(texto,), daemon=True).start()

    def _trabalhar(self, texto: str) -> None:
        try:
            resposta, encerrar = self.nucleo.processar(texto)
        except Exception as erro:  # a janela não pode fechar por causa de um erro
            resposta, encerrar = f"Algo deu errado: {erro}", False
        self.fila.put(("resposta", resposta, encerrar))

    def _ocupar(self, ocupado: bool) -> None:
        self.ocupado = ocupado
        self.botao.configure(state="disabled" if ocupado else "normal")
        self.campo.configure(state="disabled" if ocupado else "normal")
        if not ocupado:
            self.campo.focus_set()

    def _checar_fila(self) -> None:
        encerrar = False
        while True:
            try:
                item = self.fila.get_nowait()
            except queue.Empty:
                break
            if item[0] == "resposta":
                _, resposta, sair = item
                self.escrever("JARVIS", resposta, "jarvis")
                self._ocupar(False)
                encerrar = encerrar or sair
            elif item[0] == "aviso":
                self.escrever("Lembrete", item[1], "aviso")
        if encerrar:
            self.raiz.after(800, self.raiz.destroy)
            return
        self.raiz.after(INTERVALO_MS, self._checar_fila)

    # ---- configurações -------------------------------------------------------

    def abrir_configuracoes(self) -> None:
        janela = tk.Toplevel(self.raiz)
        janela.title("Configurações do JARVIS")
        janela.configure(bg=COR_FUNDO)
        janela.transient(self.raiz)
        tk.Label(janela, text="Deixe um campo vazio para manter o valor salvo.",
                 fg=COR_TEXTO, bg=COR_FUNDO).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 6))
        campos = {}
        for linha, (nome, texto, secreto) in enumerate(PERGUNTAS, start=1):
            rotulo = texto.split(" (")[0].split(" [")[0]
            tk.Label(janela, text=rotulo, fg=COR_TEXTO, bg=COR_FUNDO, anchor="w",
                     wraplength=260, justify="left").grid(row=linha, column=0, sticky="w", padx=12, pady=4)
            entrada = tk.Entry(janela, width=44, bg=COR_CAMPO, fg=COR_TEXTO, insertbackground=COR_TEXTO,
                               show="\u2022" if secreto else "", relief="flat")
            entrada.grid(row=linha, column=1, sticky="we", padx=12, pady=4)
            campos[nome] = entrada
        estado = tk.Label(janela, text="", fg=COR_JARVIS, bg=COR_FUNDO)
        estado.grid(row=len(PERGUNTAS) + 1, column=0, columnspan=2, sticky="w", padx=12)

        def salvar() -> None:
            caminho = salvar_valores({nome: e.get() for nome, e in campos.items()})
            estado.configure(text="Salvo em " + caminho)
            for e in campos.values():
                e.delete(0, "end")

        botoes = tk.Frame(janela, bg=COR_FUNDO)
        botoes.grid(row=len(PERGUNTAS) + 2, column=0, columnspan=2, sticky="e", padx=12, pady=12)
        tk.Button(botoes, text="Salvar", command=salvar).pack(side="left", padx=4)
        tk.Button(botoes, text="Fechar", command=janela.destroy).pack(side="left", padx=4)
        janela.columnconfigure(1, weight=1)


def iniciar() -> None:
    raiz = tk.Tk()
    Janela(raiz)
    raiz.mainloop()
