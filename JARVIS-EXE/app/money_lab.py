"""JARVIS MONEY — painel de análise e simulação, sem execução financeira real.

Não conecta corretoras, não envia ordens e não movimenta dinheiro.
A integração futura com dados de mercado deve identificar claramente a fonte,
o horário da cotação e indisponibilidades, sem fabricar preços ou previsões.
"""
import tkinter as tk
from tkinter import ttk

BG = "#07111f"
PANEL = "#0c1b2c"
CARD = "#10243a"
CYAN = "#42d9ff"
TEXT = "#e8f6ff"
MUTED = "#8ba9bd"


class MoneyLab:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("JARVIS MONEY — Inteligência de mercado")
        self.win.geometry("980x680")
        self.win.minsize(760, 560)
        self.win.configure(bg=BG)
        self._styles()
        self._build()

    def _styles(self):
        style = ttk.Style(self.win)
        style.theme_use("clam")
        style.configure("Money.TButton", background="#12344c", foreground=TEXT,
                        padding=(12, 9), borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Money.TButton", background=[("active", "#18516d")],
                  foreground=[("disabled", MUTED)])
        style.configure("Money.TCombobox", fieldbackground=CARD, background=CARD,
                        foreground=TEXT, arrowcolor=CYAN)

    def _build(self):
        header = tk.Frame(self.win, bg=PANEL, padx=22, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="JARVIS MONEY", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(header, text="INTELIGÊNCIA DE MERCADO • ANÁLISE • CONTROLE DE RISCO",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))

        body = tk.Frame(self.win, bg=BG, padx=20, pady=18)
        body.pack(fill="both", expand=True)
        notice = tk.Frame(body, bg="#172b3d", padx=14, pady=12,
                          highlightthickness=1, highlightbackground="#28506a")
        notice.pack(fill="x", pady=(0, 14))
        tk.Label(notice, text="MODO DE ANÁLISE — SEM ORDENS REAIS",
                 bg="#172b3d", fg=CYAN, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(notice,
                 text="Este painel ainda não está conectado a uma fonte de cotações. "
                      "Não há preços ao vivo, previsões ou operações em execução.",
                 bg="#172b3d", fg=TEXT, wraplength=850, justify="left",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

        cards = tk.Frame(body, bg=BG)
        cards.pack(fill="x")
        for title, value, desc in [
            ("DADOS DE MERCADO", "NÃO CONECTADO", "Fonte e horário serão exibidos quando integrados."),
            ("ANÁLISE IA", "AGUARDANDO DADOS", "Sem sinais ou probabilidades inventadas."),
            ("SIMULADOR", "DESLIGADO", "Nenhum saldo fictício ou operação foi iniciada."),
        ]:
            card = tk.Frame(cards, bg=CARD, padx=14, pady=16,
                            highlightthickness=1, highlightbackground="#1b3b53")
            card.pack(side="left", fill="both", expand=True, padx=(0, 10))
            tk.Label(card, text=title, bg=CARD, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")
            tk.Label(card, text=value, bg=CARD, fg=CYAN,
                     font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=8)
            tk.Label(card, text=desc, bg=CARD, fg=TEXT, wraplength=230,
                     justify="left", font=("Segoe UI", 8)).pack(anchor="w")

        section = tk.Frame(body, bg=PANEL, padx=16, pady=14)
        section.pack(fill="both", expand=True, pady=(16, 0))
        tk.Label(section, text="PLANO DO MÓDULO", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        items = [
            "• Conectar fontes legítimas de cotações e registrar fonte/horário.",
            "• Analisar tendência, volume, volatilidade, notícias e indicadores.",
            "• Exibir cenários e incerteza; nunca tratar previsão como certeza.",
            "• Testar estratégias com histórico e simulação usando cotações reais.",
            "• Aplicar limites de risco, custos, slippage e interrupção de segurança.",
            "• Registrar cada sinal, decisão, resultado e motivo para auditoria.",
        ]
        for item in items:
            tk.Label(section, text=item, bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 9), anchor="w").pack(fill="x", pady=4)
        tk.Label(section,
                 text="Não realiza apostas, não conecta corretoras e não movimenta dinheiro.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "italic")).pack(anchor="w", pady=(12, 0))
