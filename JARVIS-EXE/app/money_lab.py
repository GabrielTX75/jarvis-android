"""JARVIS MONEY — painel de análise e simulação, sem execução financeira real.

Não conecta corretoras, não envia ordens e não movimenta dinheiro.
A integração futura com dados de mercado deve identificar claramente a fonte,
o horário da cotação e indisponibilidades, sem fabricar preços ou previsões.
"""
import tkinter as tk
from tkinter import ttk
import threading
from api_services import ApiServiceError, brapi_quote

BG = "#07111f"
PANEL = "#0c1b2c"
CARD = "#10243a"
CYAN = "#42d9ff"
TEXT = "#e8f6ff"
MUTED = "#8ba9bd"


class MoneyLab:
    def __init__(self, parent, api_key=None):
        self.api_key = api_key or ""
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
                 text="Consulta de cotações reais via brapi quando o token estiver configurado. "
                      "Os dados podem ter atraso; nenhuma ordem ou transação é realizada.",
                 bg="#172b3d", fg=TEXT, wraplength=850, justify="left",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))

        quote_box = tk.Frame(body, bg=PANEL, padx=14, pady=12)
        quote_box.pack(fill="x", pady=(0, 14))
        tk.Label(quote_box, text="CONSULTAR ATIVO", bg=PANEL, fg=CYAN, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        quote_row = tk.Frame(quote_box, bg=PANEL)
        quote_row.pack(fill="x", pady=(8, 4))
        self.ticker = tk.StringVar(value="PETR4")
        ttk.Entry(quote_row, textvariable=self.ticker, width=18).pack(side="left", padx=(0, 8))
        self.quote_button = ttk.Button(quote_row, text="Consultar cotação", style="Money.TButton", command=self.fetch_quote)
        self.quote_button.pack(side="left")
        self.quote_status = tk.StringVar(value="Token brapi configurado." if self.api_key else "Adicione o token brapi em Configurações > Cofre de APIs.")
        tk.Label(quote_box, textvariable=self.quote_status, bg=PANEL, fg=MUTED, wraplength=850, justify="left").pack(anchor="w", pady=(5, 0))

        cards = tk.Frame(body, bg=BG)
        cards.pack(fill="x")
        for title, value, desc in [
            ("DADOS DE MERCADO", "BRAPI • CONSULTA", "Preço e variação aparecem após consultar um ativo."),
            ("ANÁLISE IA", "NÃO ATIVADA", "Ainda não gera análises automáticas nem recomendações."),
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

    def fetch_quote(self):
        symbol = self.ticker.get().strip().upper()
        if not self.api_key:
            self.quote_status.set("Token brapi não configurado. Abra Configurações > Cofre de APIs.")
            return
        self.quote_button.configure(state="disabled")
        self.quote_status.set("Consultando a fonte de mercado…")
        def worker():
            try:
                data = brapi_quote(self.api_key, symbol)
                price = data.get("price")
                if not isinstance(price, (int, float)):
                    raise ApiServiceError("A fonte não retornou um preço válido.")
                change = data.get("change")
                change_text = (" | variação {:+.2f}%".format(change) if isinstance(change, (int, float)) else "")
                message = "{} — {}\nPreço informado: {:.2f} {}{}\nFonte: brapi | Referência: {}\nCotação informativa; pode haver atraso e não é recomendação.".format(data["symbol"], data["name"], price, data["currency"], change_text, data.get("updated") or "horário não informado")
            except Exception as exc:
                message = str(exc)
            self.win.after(0, lambda value=message: self.quote_status.set(value))
            self.win.after(0, lambda: self.quote_button.configure(state="normal"))
        threading.Thread(target=worker, daemon=True).start()
