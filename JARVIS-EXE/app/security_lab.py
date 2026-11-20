"""JARVIS Security Lab: defensive review and bounded Red Team learning.

The Red Team profile is an educational, non-networked scenario simulator.
It does not scan arbitrary hosts, exploit services, collect credentials,
exfiltrate data, evade detection, persist, or modify target systems.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from defensive_audit import audit_folder
from security_monitor import SecurityMonitor, JsonlLogWatcher

BG = "#07111f"
PANEL = "#0b1d2e"
CARD = "#10243a"
CYAN = "#48dcff"
TEXT = "#e8f6ff"
MUTED = "#91aabd"


class SecurityLab:
    def __init__(self, parent, on_report=None):
        self.on_report = on_report
        self.log_watcher = None
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
        monitor = tk.Frame(tabs, bg=BG, padx=18, pady=18)
        tabs.add(blue, text="Auditoria local")
        tabs.add(monitor, text="Monitoramento")
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

        tk.Label(monitor, text="Monitoramento contínuo de eventos do projeto",
                 bg=BG, fg=CYAN, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(monitor,
                 text="Conecte um arquivo JSONL de auditoria exportado pelo seu próprio serviço. "
                      "O JARVIS acompanha novas linhas e identifica padrões; sem um adaptador "
                      "específico do provedor, a resposta fica em modo de simulação (sem bloquear contas).",
                 bg=BG, fg=TEXT, wraplength=780, justify="left").pack(anchor="w", pady=(8, 12))
        controls = tk.Frame(monitor, bg=BG)
        controls.pack(anchor="w", fill="x")
        ttk.Button(controls, text="Conectar log do projeto", style="Security.TButton",
                   command=self.start_log_monitor).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Parar monitoramento", style="Security.TButton",
                   command=self.stop_log_monitor).pack(side="left")
        self.monitor_status = tk.StringVar(value="MONITORAMENTO DESLIGADO")
        tk.Label(monitor, textvariable=self.monitor_status, bg=BG, fg=CYAN,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 4))
        self.monitor_result = tk.Text(monitor, height=12, bg=CARD, fg=TEXT,
                                      insertbackground=TEXT, relief="flat", wrap="word",
                                      padx=12, pady=12)
        self.monitor_result.pack(fill="both", expand=True, pady=(8, 0))
        self.monitor_result.insert("end", "Aguardando conexão com um log de eventos.\n")
        self.monitor_result.configure(state="disabled")
        self.win.protocol("WM_DELETE_WINDOW", self.close)

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


    def start_log_monitor(self):
        path = filedialog.askopenfilename(parent=self.win,
                                          title="Selecione o log JSONL do seu projeto",
                                          filetypes=[("Logs JSONL", "*.jsonl"), ("Todos", "*.*")])
        if not path:
            return
        self.stop_log_monitor()
        monitor = SecurityMonitor()
        self.log_watcher = JsonlLogWatcher(
            path, monitor,
            on_alert=lambda alert: self.win.after(0, self._display_alert, alert)
        )
        try:
            self.log_watcher.start()
            self.monitor_status.set("MONITORANDO NOVOS EVENTOS • RESPOSTA EM SIMULAÇÃO")
            self._append_monitor("Conectado ao arquivo. Eventos antigos foram ignorados; aguardando novos eventos.")
        except Exception as exc:
            self.log_watcher = None
            messagebox.showerror("Monitoramento", str(exc), parent=self.win)

    def stop_log_monitor(self):
        if self.log_watcher:
            self.log_watcher.stop()
            self.log_watcher = None
        if hasattr(self, "monitor_status"):
            self.monitor_status.set("MONITORAMENTO DESLIGADO")

    def _append_monitor(self, message):
        self.monitor_result.configure(state="normal")
        self.monitor_result.insert("end", message + "\\n")
        self.monitor_result.see("end")
        self.monitor_result.configure(state="disabled")

    def _display_alert(self, alert):
        line = (f"[{alert['severity']}] {alert['event_type']} • "
                f"ator={alert['actor_id']} • {alert['reason']} • ação={alert['action']}")
        self._append_monitor(line)
        if self.on_report:
            self.on_report("ALERTA DE SEGURANÇA", line)

    def close(self):
        self.stop_log_monitor()
        self.win.destroy()

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
