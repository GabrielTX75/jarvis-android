"""JARVIS Security Lab: defensive review and bounded Red Team learning.

The Red Team profile is an educational, non-networked scenario simulator.
It does not scan arbitrary hosts, exploit services, collect credentials,
exfiltrate data, evade detection, persist, or modify target systems.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from defensive_audit import audit_folder

BG = "#07111f"
PANEL = "#0b1d2e"
CARD = "#10243a"
CYAN = "#48dcff"
TEXT = "#e8f6ff"
MUTED = "#91aabd"


class SecurityLab:
    def __init__(self, parent, on_report=None):
        self.on_report = on_report
        self.win = tk.Toplevel(parent)
        self.win.title("JARVIS — Security Lab")
        self.win.geometry("900x650")
        self.win.minsize(720, 520)
        self.win.configure(bg=BG)
        self._styles()
        self._build()

    def _styles(self):
        style = ttk.Style(self.win)
        style.theme_use("clam")
        style.configure("Security.TButton", background="#12344c", foreground=TEXT,
                        padding=(12, 9), borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Security.TButton", background=[("active", "#18516d")])

    def _build(self):
        head = tk.Frame(self.win, bg=PANEL, padx=20, pady=16)
        head.pack(fill="x")
        tk.Label(head, text="JARVIS SECURITY LAB", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(head, text="BLUE TEAM • RED TEAM • ESCOPO AUTORIZADO",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(3, 0))

        tabs = ttk.Notebook(self.win)
        tabs.pack(fill="both", expand=True, padx=16, pady=16)
        blue = tk.Frame(tabs, bg=BG, padx=18, pady=18)
        red = tk.Frame(tabs, bg=BG, padx=18, pady=18)
        tabs.add(blue, text="Defensivo • Blue Team")
        tabs.add(red, text="Atacante • Red Team")

        tk.Label(blue, text="Análise defensiva de um projeto seu",
                 bg=BG, fg=CYAN, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(blue,
                 text="Selecione uma pasta local que você possui ou tem autorização para revisar. "
                      "A análise atual é estática e procura padrões que merecem revisão; não comprova falhas.",
                 bg=BG, fg=TEXT, wraplength=780, justify="left").pack(anchor="w", pady=(8, 14))
        ttk.Button(blue, text="Selecionar pasta e analisar", style="Security.TButton",
                   command=self.run_defensive).pack(anchor="w")
        self.blue_result = tk.Text(blue, height=13, bg=CARD, fg=TEXT, insertbackground=TEXT,
                                   relief="flat", wrap="word", padx=12, pady=12)
        self.blue_result.pack(fill="both", expand=True, pady=(14, 0))
        self.blue_result.insert("end", "Nenhuma análise executada nesta sessão.")
        self.blue_result.configure(state="disabled")

        tk.Label(red, text="Simulação controlada de Red Team",
                 bg=BG, fg=CYAN, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(red,
                 text="Treine o raciocínio de um teste de segurança em um cenário fictício local. "
                      "O módulo não envia tráfego, não testa sites reais e não explora sistemas.",
                 bg=BG, fg=TEXT, wraplength=780, justify="left").pack(anchor="w", pady=(8, 14))
        tk.Label(red, text="Cenário de treinamento", bg=BG, fg=MUTED).pack(anchor="w")
        self.scenario = tk.StringVar(value="Aplicação web fictícia com autenticação")
        ttk.Combobox(red, textvariable=self.scenario, state="readonly",
                     values=("Aplicação web fictícia com autenticação",
                             "API fictícia com controle de acesso",
                             "Servidor fictício com configuração insegura")).pack(fill="x", pady=(4, 12))
        ttk.Button(red, text="Executar simulação educativa", style="Security.TButton",
                   command=self.run_redteam).pack(anchor="w")
        self.red_result = tk.Text(red, height=13, bg=CARD, fg=TEXT, insertbackground=TEXT,
                                  relief="flat", wrap="word", padx=12, pady=12)
        self.red_result.pack(fill="both", expand=True, pady=(14, 0))
        self.red_result.insert("end", "Escolha um cenário e inicie a simulação.")
        self.red_result.configure(state="disabled")

    def _show(self, widget, value):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", value)
        widget.configure(state="disabled")

    def run_defensive(self):
        folder = filedialog.askdirectory(parent=self.win,
                                         title="Escolha um projeto seu/autorizado")
        if not folder:
            return
        if not messagebox.askyesno("Confirmar escopo",
                                   "Confirma que esta pasta é sua ou que você tem autorização para analisá-la?",
                                   parent=self.win):
            return
        try:
            findings = audit_folder(folder)
            lines = [f"Revisão concluída: {len(findings)} ocorrência(s).",
                     "Ocorrências não provam vulnerabilidade; revise o contexto manualmente.", ""]
            for item in findings[:80]:
                lines.append(f"{item['file']}:{item['line']} — {item['pattern']}")
            if not findings:
                lines.append("Nenhum padrão da lista básica foi encontrado. Isso não garante segurança.")
            report = "\n".join(lines)
            self._show(self.blue_result, report)
            if self.on_report:
                self.on_report("BLUE TEAM", report)
        except Exception as exc:
            messagebox.showerror("Análise defensiva", str(exc), parent=self.win)

    def run_redteam(self):
        scenario = self.scenario.get()
        report = (
            f"CENÁRIO FICTÍCIO: {scenario}\n\n"
            "1. Defina o ativo de laboratório e a autorização por escrito.\n"
            "2. Identifique dados e funções que precisam de proteção.\n"
            "3. Revise autenticação, autorização, validação de entradas e registros.\n"
            "4. Use contas e dados sintéticos; não use credenciais reais.\n"
            "5. Registre evidências mínimas, sem coletar dados pessoais.\n"
            "6. Corrija os problemas e repita a validação.\n\n"
            "RESULTADO: roteiro de exercício educativo gerado. Nenhum host foi contatado, "
            "nenhum exploit foi executado e nenhum dado foi acessado."
        )
        self._show(self.red_result, report)
        if self.on_report:
            self.on_report("RED TEAM — SIMULAÇÃO", report)
