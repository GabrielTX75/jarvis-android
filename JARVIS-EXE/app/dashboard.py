"""JARVIS EXE holographic command-center UI.

Real system values are shown only when the OS exposes them. Optional voice and
system-monitoring dependencies fail closed with an explanatory message.
"""
import json
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
from urllib.parse import quote_plus

import keyring
from desktop_tools import capture_screen
from project_workspace import create_project, write_project_file
from defensive_audit import audit_folder
from hologram_lab import HologramLab
from money_lab import MoneyLab
from security_lab import SecurityLab

try:
    import psutil
except Exception:
    psutil = None
try:
    import speech_recognition as sr
except Exception:
    sr = None
try:
    import pyttsx3
except Exception:
    pyttsx3 = None

APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "Jarvis"
CONFIG_FILE = APP_DIR / "settings.json"
BG = "#030b15"
PANEL = "#071827"
CARD = "#0a2033"
CARD2 = "#0c2940"
CYAN = "#39d9ff"
BLUE = "#168dff"
TEXT = "#eaf8ff"
MUTED = "#82a9bf"
GREEN = "#31e58d"
AMBER = "#ffbd4a"
RED = "#ff667a"

SYSTEM = (
    "Você é o JARVIS, assistente em português do Brasil. Seja claro, útil e honesto. "
    "Não diga que executou ações no computador; este chat não executa ferramentas por conta própria. "
    "Quando o usuário pedir uma ação, explique qual botão ou módulo pode executá-la. "
    "Nunca invente dados do sistema, localização, preços ou resultados de auditoria."
)

class JarvisApp:
    def __init__(self, root):
        self.root = root
        root.title("JARVIS — Central de Comando")
        root.geometry("1500x940")
        root.minsize(1120, 740)
        root.configure(bg=BG)
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()
        self.history = [{"role": "system", "content": SYSTEM}]
        self.busy = False
        self.voice_busy = False
        self.monitor_open = False
        self.started_at = time.time()
        self.status = tk.StringVar(value="PRONTO")
        self.connection = tk.StringVar(value="IA NÃO CONFIGURADA")
        self.location = tk.StringVar(value="Localização: não configurada")
        self._build()
        self.ai_state.set("IA: configurada" if keyring.get_password("JARVIS", "api_key") else "IA: não configurada")
        self.location.set("Localização: " + (self.config.get("location_label") or "não configurada"))
        self._tick()
        self.add("JARVIS", "Central de comando iniciada. Configure a IA para conversar.")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def load_config(self):
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        return {
            "endpoint": data.get("endpoint", "https://api.groq.com/openai/v1/chat/completions"),
            "model": data.get("model", "openai/gpt-oss-120b"),
            "api_key": keyring.get_password("JARVIS", "api_key") or "",
            "location_label": data.get("location_label", "")
        }

    def save_config(self):
        safe = {k: v for k, v in self.config.items() if k != "api_key"}
        CONFIG_FILE.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")

    def panel(self, parent, title=None, padding=12):
        box = tk.Frame(parent, bg=PANEL, padx=padding, pady=padding,
                       highlightthickness=1, highlightbackground="#174763")
        if title:
            tk.Label(box, text=title.upper(), bg=PANEL, fg=CYAN,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 9))
        return box

    def button(self, parent, text, command, accent=False, compact=False):
        return tk.Button(
            parent, text=text, command=command, cursor="hand2",
            bg=("#075d85" if accent else "#0b2b43"),
            fg=TEXT, activebackground=("#087eaa" if accent else "#124361"),
            activeforeground="white", relief="flat", bd=0,
            padx=(10 if compact else 13), pady=(7 if compact else 10),
            font=("Segoe UI", 9, "bold"), anchor="w"
        )

    def _build(self):
        self._styles()
        header = tk.Frame(self.root, bg="#061625", padx=18, pady=10,
                          highlightthickness=1, highlightbackground="#16445d")
        header.pack(fill="x")
        brand = tk.Frame(header, bg="#061625")
        brand.pack(side="left")
        tk.Label(brand, text="◈  J A R V I S", bg="#061625", fg=CYAN,
                 font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(brand, text="PERSONAL INTELLIGENCE • COMMAND SYSTEM",
                 bg="#061625", fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        center = tk.Frame(header, bg="#061625")
        center.pack(side="left", expand=True)
        self.status_label = tk.Label(center, textvariable=self.status, bg="#08283a",
                                     fg=GREEN, font=("Segoe UI", 10, "bold"),
                                     padx=20, pady=8, highlightthickness=1,
                                     highlightbackground="#14627d")
        self.status_label.pack()
        right = tk.Frame(header, bg="#061625")
        right.pack(side="right")
        self.clock = tk.Label(right, text="--:--:--", bg="#061625", fg=TEXT,
                              font=("Segoe UI", 18, "bold"))
        self.clock.pack(anchor="e")
        self.date_label = tk.Label(right, text="", bg="#061625", fg=MUTED,
                                   font=("Segoe UI", 8))
        self.date_label.pack(anchor="e")

        nav = tk.Frame(self.root, bg="#071b2b", padx=14, pady=7)
        nav.pack(fill="x")
        for label, action in [
            ("⌂  INÍCIO", self.focus_chat), ("✧  IA", self.focus_chat),
            ("▣  PROJETOS", self.new_project), ("⬡  SEGURANÇA", self.open_security_lab),
            ("⌘  CONTROLE", self.tools), ("⚙  CONFIGURAÇÕES", self.settings)
        ]:
            self.button(nav, label, action, compact=True).pack(side="left", padx=4)

        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=10, pady=10)
        shell.grid_columnconfigure(0, minsize=250, weight=0)
        shell.grid_columnconfigure(1, weight=1)
        shell.grid_columnconfigure(2, minsize=260, weight=0)
        shell.grid_rowconfigure(0, weight=1)

        left = tk.Frame(shell, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        modules = self.panel(left, "Módulos do JARVIS", 11)
        modules.pack(fill="both", expand=True)
        module_items = [
            ("▣  Controle do computador", self.tools),
            ("▦  Criar / gerenciar projetos", self.new_project),
            ("⌕  Auditoria de projetos", self.audit_local),
            ("⬡  Security Lab", self.open_security_lab),
            ("◉  Monitoramento defensivo", self.open_security_lab),
            ("◈  JARVIS Money", self.open_money_lab),
            ("➤  JARVIS Drive", self.drive),
            ("⌘  Geração de códigos", self.focus_chat),
            ("◇  Hologram Lab 3D", self.open_hologram_lab),
            ("▤  Arquivos e notas", self.open_projects_folder),
            ("⚙  Configurações", self.settings)
        ]
        for label, command in module_items:
            self.button(modules, label, command, compact=True).pack(fill="x", pady=3)
        tk.Label(modules, text="Módulos externos e integrações aparecem como desconectados até serem configurados.",
                 bg=PANEL, fg=MUTED, wraplength=210, justify="left",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(10, 0))

        center_col = tk.Frame(shell, bg=BG)
        center_col.grid(row=0, column=1, sticky="nsew", padx=5)
        center_col.grid_rowconfigure(0, weight=4)
        center_col.grid_rowconfigure(1, weight=3)
        center_col.grid_columnconfigure(0, weight=1)

        hero = tk.Frame(center_col, bg="#041321", highlightthickness=1,
                        highlightbackground="#16749a")
        hero.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_rowconfigure(0, weight=1)
        self.hero = tk.Canvas(hero, bg="#041321", highlightthickness=0)
        self.hero.grid(row=0, column=0, sticky="nsew")
        self.hero.bind("<Configure>", lambda _e: self.draw_core())
        self.hero.bind("<Button-1>", lambda _e: self.focus_chat())
        self.hero_phase = 0

        chat_panel = self.panel(center_col, None, 10)
        chat_panel.grid(row=1, column=0, sticky="nsew")
        chat_panel.grid_rowconfigure(1, weight=1)
        chat_panel.grid_columnconfigure(0, weight=1)
        tk.Label(chat_panel, text="CONVERSA COM O JARVIS", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.chat = tk.Text(chat_panel, bg="#041321", fg=TEXT, insertbackground=TEXT,
                            wrap="word", font=("Segoe UI", 9), relief="flat",
                            padx=12, pady=10, state="disabled", height=8)
        self.chat.grid(row=1, column=0, sticky="nsew")
        self.chat.tag_configure("speaker", foreground=CYAN, font=("Segoe UI", 9, "bold"))
        self.chat.tag_configure("error", foreground=RED)
        input_row = tk.Frame(chat_panel, bg=PANEL)
        input_row.grid(row=2, column=0, sticky="ew", pady=(9, 0))
        input_row.grid_columnconfigure(0, weight=1)
        self.entry = tk.Entry(input_row, bg="#09243a", fg=TEXT, insertbackground=TEXT,
                              relief="flat", font=("Segoe UI", 10))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=9, padx=(0, 7))
        self.entry.bind("<Return>", lambda _e: self.send())
        self.button(input_row, "🎙 FALAR", self.listen, compact=True).grid(row=0, column=1, padx=3)
        self.button(input_row, "ENVIAR ➤", self.send, accent=True, compact=True).grid(row=0, column=2, padx=3)

        quick = tk.Frame(center_col, bg=BG)
        quick.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        quick_actions = [
            ("🎙 VOZ", self.listen), ("▶ EXECUTAR FERRAMENTA", self.tools),
            ("✧ IA AVANÇADA", self.settings), ("⬡ SECURITY LAB", self.open_security_lab),
            ("🛡 DEFESA", self.open_security_lab)
        ]
        for i, (label, action) in enumerate(quick_actions):
            quick.grid_columnconfigure(i, weight=1)
            self.button(quick, label, action, accent=(i == 0), compact=True).grid(
                row=0, column=i, sticky="ew", padx=2)

        right = tk.Frame(shell, bg=BG)
        right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        status = self.panel(right, "Status do sistema", 11)
        status.pack(fill="x", pady=(0, 8))
        self.ai_state = tk.StringVar(value="IA: não configurada")
        self.net_state = tk.StringVar(value="Internet: não verificada")
        self.security_state = tk.StringVar(value="Defesa: monitor desligado")
        self.cpu_state = tk.StringVar(value="CPU: indisponível")
        self.mem_state = tk.StringVar(value="Memória: indisponível")
        self.disk_state = tk.StringVar(value="Disco: indisponível")
        self.battery_state = tk.StringVar(value="Bateria: indisponível")
        for var in [self.ai_state, self.net_state, self.security_state,
                    self.cpu_state, self.mem_state, self.disk_state, self.battery_state]:
            tk.Label(status, textvariable=var, bg=PANEL, fg=TEXT,
                     font=("Segoe UI", 8), anchor="w").pack(fill="x", pady=3)

        location = self.panel(right, "Redes e localização", 11)
        location.pack(fill="x", pady=(0, 8))
        tk.Label(location, textvariable=self.location, bg=PANEL, fg=TEXT,
                 wraplength=220, justify="left", font=("Segoe UI", 8)).pack(anchor="w")
        self.button(location, "ABRIR MAPA", self.drive, compact=True).pack(fill="x", pady=(8, 0))

        quick_tools = self.panel(right, "Ferramentas rápidas", 11)
        quick_tools.pack(fill="x", pady=(0, 8))
        for label, action in [
            ("▣  Calculadora", lambda: self.open_app("calc.exe", "Calculadora")),
            ("▤  Bloco de notas", lambda: self.open_app("notepad.exe", "Bloco de Notas")),
            ("🌐  Navegador", self.open_browser),
            ("📁  Abrir projetos", self.open_projects_folder),
            ("⌖  Planejar rota", self.drive),
            ("▧  Capturar tela", self.screen_capture)
        ]:
            self.button(quick_tools, label, action, compact=True).pack(fill="x", pady=2)

        self.footer = tk.Label(self.root, text="JARVIS • Aguardando comandos • Indicadores sem fonte aparecem como indisponíveis",
                               bg="#061625", fg=MUTED, font=("Segoe UI", 8), pady=7)
        self.footer.pack(fill="x")

    def _styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Jarvis.TButton", background="#0b2b43", foreground=TEXT,
                        padding=(10, 8), borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Jarvis.TButton", background=[("active", "#14506d")])

    def draw_core(self):
        if not hasattr(self, "hero"):
            return
        c = self.hero
        c.delete("all")
        w = max(c.winfo_width(), 500)
        h = max(c.winfo_height(), 260)
        cx, cy = w * .50, h * .49
        # Subtle grid and HUD rings
        for x in range(0, w, 34):
            c.create_line(x, 0, x, h, fill="#08243a")
        for y in range(0, h, 28):
            c.create_line(0, y, w, y, fill="#08243a")
        for r in [55, 78, 104, 132]:
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#0b5070", width=1)
        c.create_oval(cx-42, cy-42, cx+42, cy+42, outline=CYAN, width=2)
        c.create_oval(cx-32, cy-32, cx+32, cy+32, outline=BLUE, width=2)
        c.create_oval(cx-20, cy-20, cx+20, cy+20, fill="#0a4564", outline=CYAN, width=2)
        c.create_text(cx, cy, text="J", fill="#d9fbff", font=("Segoe UI", 30, "bold"))
        c.create_text(26, 24, anchor="nw", text="JARVIS CORE • HOLOGRAPHIC COMMAND",
                      fill=CYAN, font=("Segoe UI", 9, "bold"))
        c.create_text(26, 52, anchor="nw", text="“Como posso ajudar hoje?”",
                      fill=TEXT, font=("Segoe UI", 17, "bold"))
        c.create_text(26, 82, anchor="nw", text="IA • PROJETOS • SEGURANÇA • CONTROLE",
                      fill=MUTED, font=("Segoe UI", 8, "bold"))
        c.create_text(w-22, 24, anchor="ne", text=self.status.get(),
                      fill=GREEN, font=("Segoe UI", 9, "bold"))
        c.create_text(w-22, h-20, anchor="se",
                      text="Núcleo visual • sem projeção holográfica física",
                      fill=MUTED, font=("Segoe UI", 7))
        self.hero_phase = (self.hero_phase + 1) % 100
        # Orbit markers
        import math
        for j in range(5):
            a = self.hero_phase * .035 + j * (math.tau / 5)
            px, py = cx + math.cos(a) * 118, cy + math.sin(a) * 118
            c.create_oval(px-3, py-3, px+3, py+3, fill=CYAN, outline="")
        self.root.after(80, self.draw_core)

    def _tick(self):
        now = time.localtime()
        self.clock.configure(text=time.strftime("%H:%M:%S", now))
        self.date_label.configure(text=time.strftime("%d/%m/%Y", now))
        self._system_stats()
        self.root.after(3000, self._tick)

    def _system_stats(self):
        if psutil is None:
            self.cpu_state.set("CPU: instale psutil")
            self.mem_state.set("Memória: instale psutil")
            self.disk_state.set("Disco: instale psutil")
            self.battery_state.set("Bateria: indisponível")
            return
        try:
            self.cpu_state.set(f"CPU: {psutil.cpu_percent()}%")
            self.mem_state.set(f"Memória: {psutil.virtual_memory().percent}%")
            self.disk_state.set(f"Disco: {psutil.disk_usage(str(Path.home().anchor or '/')).percent}%")
            battery = psutil.sensors_battery()
            self.battery_state.set(
                f"Bateria: {int(battery.percent)}%" if battery else "Bateria: não disponível neste PC"
            )
        except Exception:
            self.cpu_state.set("CPU: leitura indisponível")

    def add(self, who, msg, error=False):
        self.chat.configure(state="normal")
        self.chat.insert("end", who + "\n", "speaker")
        if error:
            self.chat.insert("end", str(msg) + "\n\n", "error")
        else:
            self.chat.insert("end", str(msg) + "\n\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def focus_chat(self):
        self.entry.focus_set()

    def send(self):
        prompt = self.entry.get().strip()
        if not prompt or self.busy:
            return
        self.entry.delete(0, "end")
        self.add("VOCÊ", prompt)
        self.history.append({"role": "user", "content": prompt})
        self.busy = True
        self.status.set("PROCESSANDO")
        self.ai_state.set("IA: processando")
        threading.Thread(target=self.ask, daemon=True).start()

    def ask(self):
        try:
            endpoint = self.config["endpoint"]
            key = keyring.get_password("JARVIS", "api_key") or ""
            model = self.config["model"]
            if not endpoint.startswith("https://"):
                raise ValueError("O endpoint remoto precisa usar HTTPS.")
            if not key or not model:
                raise ValueError("Configure modelo e chave da API.")
            body = json.dumps({
                "model": model, "messages": self.history[-24:],
                "max_completion_tokens": 8192, "stream": False
            }).encode()
            req = urllib.request.Request(endpoint, data=body, headers={
                "Content-Type": "application/json", "Authorization": "Bearer " + key
            }, method="POST")
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
            answer = data["choices"][0]["message"]["content"]
            if isinstance(answer, list):
                answer = "\n".join(x.get("text", "") for x in answer if isinstance(x, dict))
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("Resposta vazia ou formato inesperado.")
            self.history.append({"role": "assistant", "content": answer})
            self.root.after(0, lambda a=answer: self.add("JARVIS", a))
            self.root.after(0, lambda: self.status.set("ONLINE"))
            self.root.after(0, lambda: self.ai_state.set("IA: conectada"))
            if self.config.get("speak_replies"):
                self.speak(answer)
        except urllib.error.HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", "replace")
            self.root.after(0, lambda m=f"HTTP {exc.code}: {detail}": self.add("ERRO", m, True))
            self.root.after(0, lambda: self.status.set("ERRO"))
            self.root.after(0, lambda: self.ai_state.set("IA: erro"))
        except Exception as exc:
            msg = str(exc)
            self.root.after(0, lambda m=msg: self.add("ERRO", m, True))
            self.root.after(0, lambda: self.status.set("ERRO"))
        finally:
            self.busy = False

    def listen(self):
        if self.voice_busy:
            return
        if sr is None:
            messagebox.showinfo("Comandos de voz",
                "Reconhecimento de fala opcional: instale SpeechRecognition e PyAudio. A transcrição usa o serviço online do Google; não identifica o locutor. A leitura em voz alta usa síntese local quando pyttsx3 está instalado.")
            return
        self.voice_busy = True
        self.status.set("OUVINDO")
        self.add("JARVIS", "Microfone ativado. A transcrição usa o serviço online de reconhecimento do Google; não identifica quem está falando.")
        threading.Thread(target=self._listen_worker, daemon=True).start()

    def _listen_worker(self):
        try:
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=6, phrase_time_limit=12)
            text = recognizer.recognize_google(audio, language="pt-BR")
            self.root.after(0, lambda t=text: self._voice_text(t))
        except Exception as exc:
            msg = str(exc)
            self.root.after(0, lambda m=msg: self.add("VOZ", "Não foi possível reconhecer: " + m, True))
            self.root.after(0, lambda: self.status.set("PRONTO"))
        finally:
            self.voice_busy = False

    def _voice_text(self, text):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self.status.set("PRONTO")
        self.send()

    def speak(self, text):
        if pyttsx3 is None:
            self.root.after(0, lambda: self.add("VOZ", "Síntese de voz não instalada."))
            return
        def worker():
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 178)
                engine.say(text[:3500])
                engine.runAndWait()
                engine.stop()
            except Exception as exc:
                self.root.after(0, lambda: self.add("VOZ", "Falha na síntese: " + str(exc), True))
        threading.Thread(target=worker, daemon=True).start()

    def settings(self):
        win = tk.Toplevel(self.root)
        win.title("Configurações JARVIS")
        win.configure(bg=PANEL)
        fields = {}
        for label, key, secret in [
            ("Endpoint HTTPS", "endpoint", False),
            ("Modelo", "model", False),
            ("Chave da API (fica no Gerenciador de Credenciais)", "api_key", True),
            ("Localização salva (opcional; apenas rótulo)", "location_label", False)
        ]:
            tk.Label(win, text=label, bg=PANEL, fg=TEXT).pack(anchor="w", padx=16, pady=(10, 2))
            entry = tk.Entry(win, width=66, show="*" if secret else None,
                             bg="#09243a", fg=TEXT, insertbackground=TEXT, relief="flat")
            entry.insert(0, self.config.get(key, ""))
            entry.pack(padx=16, ipady=6)
            fields[key] = entry
        speak_var = tk.BooleanVar(value=bool(self.config.get("speak_replies")))
        tk.Checkbutton(win, text="Ler respostas em voz alta (síntese local)",
                       variable=speak_var, bg=PANEL, fg=TEXT, selectcolor=CARD,
                       activebackground=PANEL, activeforeground=TEXT).pack(anchor="w", padx=16, pady=10)
        tk.Label(win, text="A chave não é salva no arquivo settings.json.",
                 bg=PANEL, fg=MUTED).pack(anchor="w", padx=16, pady=6)
        def save():
            for key, entry in fields.items():
                if key != "api_key":
                    self.config[key] = entry.get().strip()
            key = fields["api_key"].get().strip()
            if key:
                keyring.set_password("JARVIS", "api_key", key)
            self.config["speak_replies"] = speak_var.get()
            self.save_config()
            self.location.set("Localização: " + (self.config["location_label"] or "não configurada"))
            self.ai_state.set("IA: configurada" if keyring.get_password("JARVIS", "api_key") else "IA: chave ausente")
            win.destroy()
            self.add("JARVIS", "Configurações salvas.")
        self.button(win, "SALVAR CONFIGURAÇÕES", save, accent=True).pack(pady=14, padx=16, fill="x")

    def tools(self):
        win = tk.Toplevel(self.root)
        win.title("Controle do computador")
        win.configure(bg=PANEL)
        tk.Label(win, text="Ações locais exigem confirmação quando aplicável.",
                 bg=PANEL, fg=CYAN).pack(padx=16, pady=12)
        actions = [
            ("Abrir Calculadora", lambda: self.open_app("calc.exe", "Calculadora")),
            ("Abrir Bloco de Notas", lambda: self.open_app("notepad.exe", "Bloco de Notas")),
            ("Abrir navegador", self.open_browser),
            ("Pesquisar na web", self.web_search),
            ("Criar projeto", self.new_project),
            ("Auditar pasta local", self.audit_local),
            ("Capturar tela", self.screen_capture),
            ("Abrir pasta de projetos", self.open_projects_folder)
        ]
        for label, action in actions:
            self.button(win, label, action, compact=True).pack(fill="x", padx=16, pady=4)

    def open_app(self, exe, label):
        if not messagebox.askyesno("Autorizar ação", f"Permitir abrir {label}?"):
            return
        try:
            subprocess.Popen([exe], shell=False)
            self.add("CONTROLE", label + " aberto.")
        except Exception as exc:
            messagebox.showerror("Controle", str(exc))

    def open_browser(self):
        if messagebox.askyesno("Autorizar ação", "Abrir o navegador padrão?"):
            webbrowser.open("https://www.google.com")
            self.add("CONTROLE", "Solicitação enviada ao navegador padrão.")

    def web_search(self):
        query = simpledialog.askstring("Pesquisa na web", "O que deseja pesquisar?")
        if query and messagebox.askyesno("Confirmar pesquisa", "Pesquisar: " + query + "?"):
            webbrowser.open("https://www.google.com/search?q=" + quote_plus(query))
            self.add("PESQUISA", "Pesquisa aberta no navegador; os resultados não foram lidos pelo JARVIS.")

    def new_project(self):
        name = simpledialog.askstring("Novo projeto", "Nome do projeto (letras, números, _ ou -):")
        if not name:
            return
        try:
            path = create_project(name)
            self.add("PROJETOS", f"Pasta criada: {path}. Arquivos não são executados automaticamente.")
            if messagebox.askyesno("Projeto criado", "Deseja criar um arquivo inicial?"):
                filename = simpledialog.askstring("Arquivo", "Nome do arquivo (ex.: index.html):")
                if filename:
                    content = simpledialog.askstring("Conteúdo", "Conteúdo inicial do arquivo:")
                    if content is not None:
                        target = write_project_file(name, filename, content)
                        self.add("PROJETOS", f"Arquivo salvo: {target}")
        except Exception as exc:
            messagebox.showerror("Projeto", str(exc))

    def audit_local(self):
        folder = filedialog.askdirectory(title="Selecione uma pasta sua/autorizada")
        if not folder:
            return
        if not messagebox.askyesno("Confirmar escopo", "Confirma que esta pasta é sua ou que você tem autorização para auditá-la?"):
            return
        try:
            findings = audit_folder(folder)
            self.add("AUDITORIA", f"{len(findings)} ocorrência(s) para revisão manual. Isso não comprova vulnerabilidade.")
            for item in findings[:40]:
                self.add("ACHADO", f"{item['file']}:{item['line']} — {item['pattern']}")
        except Exception as exc:
            messagebox.showerror("Auditoria", str(exc))

    def open_security_lab(self):
        SecurityLab(self.root, on_report=lambda mode, report: self.add(mode, report))
        self.monitor_open = True
        self.security_state.set("Defesa: configure um log para monitorar")
        self.add("SECURITY LAB", "Painel aberto. O monitor só funciona após conectar um log do seu próprio projeto.")

    def open_hologram_lab(self):
        HologramLab(self.root)
        self.add("HOLOGRAM LAB", "Laboratório 3D aberto. A câmera fica desligada até ativação manual.")

    def open_money_lab(self):
        MoneyLab(self.root)
        self.add("JARVIS MONEY", "Painel de análise aberto. Ainda sem fonte de cotações conectada.")

    def drive(self):
        destination = simpledialog.askstring("JARVIS DRIVE", "Destino para abrir no mapa:")
        if not destination:
            return
        if messagebox.askyesno("Abrir navegação", f"Abrir rota até {destination} no navegador?"):
            url = "https://www.google.com/maps/dir/?api=1&destination=" + quote_plus(destination)
            webbrowser.open(url)
            self.add("JARVIS DRIVE", "Rota aberta no Google Maps. O JARVIS não controla o veículo nem confirma sua localização atual.")

    def open_projects_folder(self):
        from project_workspace import ROOT
        ROOT.mkdir(parents=True, exist_ok=True)
        if messagebox.askyesno("Abrir projetos", f"Abrir a pasta local?\n{ROOT}"):
            try:
                os.startfile(str(ROOT))
                self.add("ARQUIVOS", f"Pasta aberta: {ROOT}")
            except Exception as exc:
                messagebox.showerror("Arquivos", str(exc))

    def screen_capture(self):
        if not messagebox.askyesno("Captura de tela", "Autoriza capturar a tela atual?"):
            return
        destination = filedialog.asksaveasfilename(defaultextension=".png",
                                                   filetypes=[("PNG", "*.png")])
        if not destination:
            return
        try:
            capture_screen(destination)
            self.add("VISÃO", f"Captura salva em {destination}.")
        except Exception as exc:
            messagebox.showerror("Captura", str(exc))

    def close(self):
        self.root.destroy()


def main():
    root = tk.Tk()
    JarvisApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
