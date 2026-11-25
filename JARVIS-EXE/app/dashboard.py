"""JARVIS EXE holographic command-center UI.

Real system values are shown only when the OS exposes them. Optional voice and
system-monitoring dependencies fail closed with an explanatory message.
"""
import json
import os
import re
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
from datetime import datetime, timedelta
from reminders import ReminderManager, parse_reminder
from core import CommandRouter, ModuleRegistry, ModuleStatus
from urllib.parse import quote_plus, quote
from api_services import ApiServiceError, brapi_quote, gemini_chat, groq_chat, tavily_search
from agents import names as agent_names, system_instruction as agent_instruction
from memory_store import LocalMemory
from voice_session import run_continuous_session

import keyring
from desktop_tools import capture_screen, read_screen_text
from project_workspace import create_project, write_project_file
from vscode_integration import create_generated_project, open_in_vscode
from defensive_audit import audit_folder
from hologram_lab import HologramLab
from money_lab import MoneyLab
from security_lab import SecurityLab
from internal_browser import InternalBrowser

try:
    from winotify import Notification, audio
except Exception:
    Notification = None
    audio = None
try:
    import psutil
except Exception:
    psutil = None
try:
    import speech_recognition as sr
except Exception:
    sr = None
try:
    import edge_tts
except Exception:
    edge_tts = None
try:
    import pygame
except Exception:
    pygame = None
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
    "Só confirme uma ação local depois que o módulo correspondente retornar sucesso. "
    "Se não houver ferramenta conectada, explique a limitação sem fingir execução. "
    "Nunca invente dados do sistema, localização, preços ou resultados de auditoria. "
    "Quando o usuário pedir explicitamente para criar um projeto ou gravar arquivos, "
    "responda normalmente e acrescente ao final um único bloco delimitado por "
    "[[JARVIS_WORKSPACE_ACTION]] e [[/JARVIS_WORKSPACE_ACTION]]. O conteúdo interno "
    "deve ser JSON válido com as chaves name e files; cada item de files tem path e content. "
    "Exemplo de estrutura: {\"name\":\"meu_app\",\"files\":[{\"path\":\"main.py\",\"content\":\"print(1)\"}]}. "
    "Não use Markdown dentro do JSON. Inclua somente arquivos de texto de código/configuração; "
    "nunca inclua segredos, executáveis ou instruções para execução automática. "
    "O JARVIS pedirá confirmação antes de gravar e abrir o VS Code. "
    "Se o usuário só pedir um exemplo ou explicação, não gere esse bloco."
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
        self.reminders = ReminderManager(APP_DIR / "reminders.json")
        self.memory = LocalMemory(APP_DIR / "memory.json")
        self.agent_var = tk.StringVar(value="Geral")
        self.command_router = CommandRouter()
        self.command_router.register("vscode", self.try_vscode_command, priority=5)
        self.command_router.register("reminders", self.try_reminder_command, priority=10)
        self.command_router.register("browser", self.try_browser_command, priority=20)
        self.modules = ModuleRegistry()
        self.modules.register(ModuleStatus("ai", "IA conversacional", ("chat",), True, "Usa o provedor configurado"))
        self.modules.register(ModuleStatus("reminders", "Lembretes", ("notifications", "calendar_local"), True, "Armazenamento local; EXE precisa permanecer aberto"))
        self.modules.register(ModuleStatus("browser", "Navegador interno", ("web_navigation",), True, "Abre páginas; pesquisa API dedicada ainda não conectada"))
        self.modules.register(ModuleStatus("maps", "Mapas e rotas", ("maps", "routes"), False, "Abre Google Maps; GPS e Routes API ainda não conectados"))
        self.modules.register(ModuleStatus("holograms", "Hologramas 3D", ("3d", "hand_tracking"), True, "Laboratório esquemático; webcam opcional"))
        self.modules.register(ModuleStatus("security", "Segurança defensiva", ("static_audit", "event_monitoring"), True, "Auditoria local e logs fornecidos; sem contenção remota"))
        self.modules.register(ModuleStatus("finance", "Análise financeira", ("market_data",), False, "Sem provedor de cotações conectado"))
        self.history = [{"role": "system", "content": SYSTEM}]
        self.busy = False
        self.voice_session_active = False
        self.voice_thread = None
        self.voice_stop_event = threading.Event()
        self.voice_resume_event = threading.Event()
        self.voice_resume_event.set()
        self.voice_error = None
        self.speech_active = False
        self.voice_button = None
        self.voice_state = None
        self.monitor_open = False
        self.internal_browser = None
        self.started_at = time.time()
        self.status = tk.StringVar(value="PRONTO")
        self.connection = tk.StringVar(value="IA NÃO CONFIGURADA")
        self.location = tk.StringVar(value="Localização: não configurada")
        self._build()
        self.ai_state.set("IA: configurada" if (keyring.get_password("JARVIS", "groq_key") or keyring.get_password("JARVIS", "api_key") or keyring.get_password("JARVIS", "gemini_key")) else "IA: não configurada")
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
            "location_label": data.get("location_label", ""),
            "speak_replies": bool(data.get("speak_replies", False))
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
        chat_header = tk.Frame(chat_panel, bg=PANEL)
        chat_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        chat_header.grid_columnconfigure(0, weight=1)
        tk.Label(chat_header, text="CONVERSA COM O JARVIS", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(chat_header, text="AGENTE", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=1, padx=(8, 4))
        self.agent_picker = ttk.Combobox(chat_header, textvariable=self.agent_var,
                                         values=agent_names(), state="readonly", width=14)
        self.agent_picker.grid(row=0, column=2, sticky="e")
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
        self.voice_button = self.button(input_row, "🎙 INICIAR ESCUTA", self.listen, compact=True)
        self.voice_button.grid(row=0, column=1, padx=3)
        self.voice_state = tk.StringVar(value="MICROFONE PRONTO • ÁUDIO ENVIADO AO GOOGLE")
        tk.Label(chat_panel, textvariable=self.voice_state, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=3, column=0, sticky="w", pady=(6, 0))
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
            ("🌐  Navegador interno", self.open_browser),
            ("▶  Abrir vídeo", self.open_video),
            ("📁  Abrir projetos", self.open_projects_folder),
            ("⌖  Planejar rota", self.drive),
            ("⏰  Meus lembretes", self.open_reminders),
            ("▧  Capturar tela", self.screen_capture),
            ("▤  Memória local", self.manage_memory)
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
        self._check_reminders()
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
        if self.try_memory_command(prompt):
            self.voice_resume_event.set()
            return
        if self.command_router.dispatch(prompt):
            self.voice_resume_event.set()
            return
        self.history.append({"role": "user", "content": prompt})
        self.busy = True
        self.status.set("PROCESSANDO")
        self.ai_state.set("IA: processando")
        threading.Thread(target=self.ask, daemon=True).start()

    def ask(self):
        try:
            request_history = [dict(item) for item in self.history]
            context = self.memory.prompt_context()
            system_text = SYSTEM + "\n\n" + agent_instruction(self.agent_var.get())
            if context:
                system_text += "\n\n" + context
            if request_history and request_history[0].get("role") == "system":
                request_history[0]["content"] = system_text
            else:
                request_history.insert(0, {"role": "system", "content": system_text})
            groq_key = keyring.get_password("JARVIS", "groq_key") or keyring.get_password("JARVIS", "api_key") or ""
            gemini_key = keyring.get_password("JARVIS", "gemini_key") or ""
            answer = None
            provider = ""
            errors = []
            if groq_key:
                try:
                    answer = groq_chat(groq_key, self.config["model"], request_history,
                                        endpoint=self.config["endpoint"])
                    provider = "Groq"
                except Exception as exc:
                    errors.append("Groq: " + str(exc))
            if answer is None and gemini_key:
                try:
                    answer = gemini_chat(gemini_key, request_history)
                    provider = "Gemini (reserva)"
                except Exception as exc:
                    errors.append("Gemini: " + str(exc))
            if answer is None:
                raise ApiServiceError("Nenhuma IA respondeu. " + " ".join(errors or ["Configure Groq ou Gemini em Configurações."]))
            workspace_action = self.extract_workspace_action(answer)
            if workspace_action:
                answer = re.sub(
                    r"\[\[JARVIS_WORKSPACE_ACTION\]\].*?\[\[/JARVIS_WORKSPACE_ACTION\]\]",
                    "", answer, flags=re.S
                ).strip()
            self.history.append({"role": "assistant", "content": answer})
            self.root.after(0, lambda a=answer, p=provider: self.add("JARVIS • " + p, a))
            if workspace_action:
                self.root.after(0, lambda action=workspace_action: self.apply_workspace_action(action))
            self.root.after(0, lambda: self.status.set("ONLINE"))
            self.root.after(0, lambda p=provider: self.ai_state.set("IA: " + p + " conectada"))
            if self.config.get("speak_replies"):
                self.speak(answer)
        except Exception as exc:
            msg = str(exc)
            self.root.after(0, lambda m=msg: self.add("ERRO", m, True))
            self.root.after(0, lambda: self.status.set("ERRO"))
            self.root.after(0, lambda: self.ai_state.set("IA: erro"))
        finally:
            self.busy = False
            if not self.speech_active:
                self.voice_resume_event.set()

    def _voice_ui(self, listening, message=None):
        if self.voice_button is not None:
            self.voice_button.configure(
                text="■ PARAR ESCUTA" if listening else "🎙 INICIAR ESCUTA",
                state="normal",
                bg="#123d58" if listening else CARD2
            )
        if self.voice_state is not None:
            self.voice_state.set(message or (
                "ESCUTA CONTÍNUA ATIVA • CLIQUE PARA PARAR"
                if listening else "MICROFONE PRONTO • ÁUDIO ENVIADO AO GOOGLE"
            ))
        self.status.set("OUVINDO" if listening else "PRONTO")

    def listen(self):
        if self.voice_session_active:
            self.stop_voice_session()
            return
        if sr is None:
            messagebox.showinfo(
                "Comandos de voz",
                "O reconhecimento de fala não está disponível. Verifique SpeechRecognition e PyAudio."
            )
            return
        if not messagebox.askyesno(
            "Escuta contínua — privacidade",
            "O JARVIS enviará o áudio capturado ao serviço de reconhecimento do Google "
            "para transcrição em português do Brasil. O JARVIS não grava o áudio em arquivo. "
            "Deseja iniciar a escuta?"
        ):
            return
        if self.voice_thread is not None and self.voice_thread.is_alive():
            messagebox.showinfo(
                "Comandos de voz",
                "A sessão anterior ainda está encerrando. Aguarde um instante."
            )
            return

        self.voice_stop_event = threading.Event()
        self.voice_resume_event = threading.Event()
        self.voice_resume_event.set()
        self.voice_error = None
        self.voice_session_active = True
        self._voice_ui(True, "ESCUTA CONTÍNUA ATIVA • CLIQUE PARA PARAR")
        self.voice_thread = threading.Thread(
            target=self._listen_session_worker,
            daemon=True,
            name="JARVIS-Voice-Session"
        )
        self.voice_thread.start()

    def stop_voice_session(self):
        if not self.voice_session_active:
            return
        self.voice_stop_event.set()
        self.voice_resume_event.set()
        if self.voice_state is not None:
            self.voice_state.set("ENCERRANDO MICROFONE...")
        self.status.set("PRONTO")

    def _listen_session_worker(self):
        try:
            run_continuous_session(
                sr,
                self.voice_stop_event,
                self.voice_resume_event,
                on_text=lambda phrase: self.root.after(
                    0, lambda value=phrase: self._voice_text(value)
                ),
                on_status=lambda message: self.root.after(
                    0,
                    lambda value=message: self.voice_state.set(value)
                    if self.voice_state is not None and self.voice_session_active else None
                ),
                on_error=self._voice_session_error
            )
        except Exception as exc:
            self.voice_error = "MICROFONE INDISPONÍVEL"
            message = str(exc)
            try:
                self.root.after(
                    0, lambda value=message: self.add(
                        "VOZ", "Falha ao ouvir: " + value, True
                    )
                )
            except Exception:
                pass
        finally:
            try:
                self.root.after(0, self._voice_session_finished)
            except Exception:
                pass

    def _voice_session_error(self, message):
        self.voice_error = message
        self.voice_stop_event.set()
        self.voice_resume_event.set()

    def _voice_session_finished(self):
        self.voice_session_active = False
        message = self.voice_error or "MICROFONE DESATIVADO"
        self._voice_ui(False, message)
        self.voice_error = None

    def _voice_text(self, text):
        if not self.voice_session_active or self.voice_stop_event.is_set():
            self.voice_resume_event.set()
            return
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        if self.voice_state is not None:
            self.voice_state.set("COMANDO RECEBIDO • PROCESSANDO")
        self.send()

    def speak(self, text):
        """Speak with a fixed Brazilian Portuguese masculine neural voice."""
        self.speech_active = True

        def worker():
            temp_path = None
            try:
                if edge_tts is not None and pygame is not None:
                    import asyncio
                    import tempfile
                    voice = "pt-BR-AntonioNeural"
                    temp = tempfile.NamedTemporaryFile(prefix="jarvis_voice_", suffix=".mp3", delete=False)
                    temp_path = temp.name
                    temp.close()
                    async def generate():
                        communicate = edge_tts.Communicate(
                            text[:3500], voice=voice, rate="-6%", volume="+0%"
                        )
                        await communicate.save(temp_path)
                    asyncio.run(generate())
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.12)
                    pygame.mixer.music.unload()
                    return
                if pyttsx3 is not None:
                    engine = pyttsx3.init()
                    male_voice = None
                    for candidate in engine.getProperty("voices"):
                        name = (getattr(candidate, "name", "") or "").lower()
                        gender = (getattr(candidate, "gender", "") or "").lower()
                        langs = " ".join(
                            x.decode("utf-8", "ignore") if isinstance(x, bytes) else str(x)
                            for x in (getattr(candidate, "languages", []) or [])
                        ).lower()
                        male_hint = gender == "male" or any(
                            token in name for token in ("male", "antonio", "daniel", "ricardo")
                        )
                        portuguese = "pt" in langs or any(
                            token in name for token in ("portugu", "brazil", "brasil")
                        )
                        if male_hint and portuguese:
                            male_voice = candidate.id
                            break
                    if male_voice:
                        engine.setProperty("voice", male_voice)
                        engine.setProperty("rate", 158)
                        engine.setProperty("volume", 0.95)
                        engine.say(text[:3500])
                        engine.runAndWait()
                        engine.stop()
                        return
                self.root.after(0, lambda: self.add(
                    "VOZ", "Voz masculina pt-BR indisponível. Instale/ative a voz neural Antonio (pt-BR) e mantenha Edge TTS e pygame instalados."
                ))
            except Exception as exc:
                msg = str(exc)
                self.root.after(0, lambda m=msg: self.add("VOZ", "Falha na voz masculina: " + m, True))
            finally:
                if temp_path:
                    try:
                        os.unlink(temp_path)
                    except OSError:
                        pass
                self.speech_active = False
                if self.voice_session_active:
                    self.voice_resume_event.set()
        try:
            threading.Thread(target=worker, daemon=True, name="JARVIS-Text-To-Speech").start()
        except Exception:
            self.speech_active = False
            self.voice_resume_event.set()
            raise

    def settings(self):
        win = tk.Toplevel(self.root)
        win.title("Configurações e Cofre de APIs — JARVIS")
        win.configure(bg=PANEL)
        win.geometry("820x860")
        fields = {}
        api_services = {
            "groq": ("Groq API Key", "groq_key"),
            "gemini": ("Gemini API Key", "gemini_key"),
            "tavily": ("Tavily API Key", "tavily_key"),
            "brapi": ("brapi Token", "brapi_key"),
        }
        for label, key, secret in [
            ("Endpoint HTTPS da IA", "endpoint", False),
            ("Modelo", "model", False),
            ("Groq API Key (armazenada no Gerenciador de Credenciais)", "api_key", True),
            ("Localização salva (opcional; apenas rótulo)", "location_label", False)
        ]:
            tk.Label(win, text=label, bg=PANEL, fg=TEXT).pack(anchor="w", padx=16, pady=(10, 2))
            entry = tk.Entry(win, width=72, show="*" if secret else None,
                             bg="#09243a", fg=TEXT, insertbackground=TEXT, relief="flat")
            if not secret:
                entry.insert(0, self.config.get(key, ""))
            entry.pack(padx=16, ipady=6)
            fields[key] = entry

        tk.Label(win, text="COFRE DE APIs — os campos secretos ficam vazios ao abrir.",
                 bg=PANEL, fg=CYAN, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        api_entries = {"groq": fields["api_key"]}
        api_status = {}
        for service, (label, credential_name) in api_services.items():
            if service == "groq":
                parent = tk.Frame(win, bg=PANEL)
                parent.pack(fill="x", padx=16, pady=3)
                status = tk.StringVar(value="Configurada" if keyring.get_password("JARVIS", credential_name) or keyring.get_password("JARVIS", "api_key") else "Não configurada")
                tk.Label(parent, text="Groq — chave acima", bg=PANEL, fg=MUTED).pack(side="left")
                tk.Label(parent, textvariable=status, bg=PANEL, fg=TEXT).pack(side="left", padx=10)
            else:
                tk.Label(win, text=label, bg=PANEL, fg=TEXT).pack(anchor="w", padx=16, pady=(7, 2))
                row = tk.Frame(win, bg=PANEL)
                row.pack(fill="x", padx=16)
                entry = tk.Entry(row, width=58, show="*", bg="#09243a", fg=TEXT,
                                 insertbackground=TEXT, relief="flat")
                entry.pack(side="left", ipady=6)
                api_entries[service] = entry
                status = tk.StringVar(value="Configurada" if keyring.get_password("JARVIS", credential_name) else "Não configurada")
                tk.Label(row, textvariable=status, bg=PANEL, fg=MUTED).pack(side="left", padx=8)
            api_status[service] = status

        def test_api(service):
            entry = api_entries[service]
            label, credential_name = api_services[service]
            key = entry.get().strip() or keyring.get_password("JARVIS", credential_name) or ""
            if not key and service == "groq":
                key = keyring.get_password("JARVIS", "api_key") or ""
            if not key:
                api_status[service].set("Informe/salve a chave primeiro")
                return

            api_status[service].set("Testando…")
            def worker():
                try:
                    if service == "groq":
                        req = urllib.request.Request("https://api.groq.com/openai/v1/models",
                            headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
                    elif service == "gemini":
                        req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?key=" + quote(key, safe=""),
                            headers={"Accept": "application/json"})
                    elif service == "tavily":
                        body = json.dumps({"api_key": key, "query": "teste de conexão", "max_results": 1}).encode()
                        req = urllib.request.Request("https://api.tavily.com/search", data=body,
                            headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
                    else:
                        req = urllib.request.Request("https://brapi.dev/api/quote/PETR4?token=" + quote(key, safe=""),
                            headers={"Accept": "application/json"})
                    with urllib.request.urlopen(req, timeout=12) as response:
                        ok = 200 <= response.status < 300
                    result = "Conexão confirmada" if ok else "Resposta inesperada"
                except urllib.error.HTTPError as exc:
                    result = "HTTP " + str(exc.code) + " — confira chave e cota"
                except Exception:
                    result = "Falha de rede ou serviço indisponível"
                self.root.after(0, lambda value=result, svc=service: api_status[svc].set(value))
            threading.Thread(target=worker, daemon=True).start()

        test_row = tk.Frame(win, bg=PANEL)
        test_row.pack(fill="x", padx=16, pady=8)
        for service in api_services:
            self.button(test_row, "TESTAR " + service.upper(),
                        lambda svc=service: test_api(svc), compact=True).pack(side="left", padx=3)

        speak_var = tk.BooleanVar(value=bool(self.config.get("speak_replies")))
        tk.Checkbutton(win, text="Ler respostas em voz alta (voz masculina pt-BR; requer internet)",
                       variable=speak_var, bg=PANEL, fg=TEXT, selectcolor=CARD,
                       activebackground=PANEL, activeforeground=TEXT).pack(anchor="w", padx=16, pady=10)
        tk.Label(win, text="As chaves são salvas no Gerenciador de Credenciais do Windows; nunca em settings.json.",
                 bg=PANEL, fg=MUTED, wraplength=700, justify="left").pack(anchor="w", padx=16, pady=6)

        def save():
            for key, entry in fields.items():
                if key not in ("api_key",):
                    self.config[key] = entry.get().strip()
            for service, entry in api_entries.items():
                value = entry.get().strip()
                if value:
                    credential_name = api_services[service][1]
                    keyring.set_password("JARVIS", credential_name, value)
                    if service == "groq":
                        keyring.set_password("JARVIS", "api_key", value)
                # Empty fields preserve existing credentials; no accidental deletion.
            self.config["speak_replies"] = speak_var.get()
            self.save_config()
            self.location.set("Localização: " + (self.config["location_label"] or "não configurada"))
            configured = bool(keyring.get_password("JARVIS", "groq_key") or keyring.get_password("JARVIS", "api_key") or keyring.get_password("JARVIS", "gemini_key"))
            self.ai_state.set("IA: configurada" if configured else "IA: chave ausente")
            win.destroy()
            self.add("JARVIS", "Configurações e cofre de APIs salvos com segurança.")

        self.button(win, "SALVAR CHAVES E CONFIGURAÇÕES", save, accent=True).pack(pady=14, padx=16, fill="x")

        def clear_api_keys():
            if not messagebox.askyesno("Apagar credenciais", "Apagar Groq, Gemini, Tavily e brapi do Gerenciador de Credenciais?"):
                return
            for _service, (_label, credential_name) in api_services.items():
                try:
                    keyring.delete_password("JARVIS", credential_name)
                except Exception:
                    pass
            try:
                keyring.delete_password("JARVIS", "api_key")
            except Exception:
                pass
            self.config["api_key"] = ""
            self.ai_state.set("IA: chave ausente")
            win.destroy()
            self.add("JARVIS", "Credenciais de API apagadas do Gerenciador de Credenciais.")

        self.button(win, "APAGAR TODAS AS CHAVES", clear_api_keys).pack(pady=(0, 12), padx=16, fill="x")

    def tools(self):
        win = tk.Toplevel(self.root)
        win.title("Controle do computador")
        win.configure(bg=PANEL)
        tk.Label(win, text="Ações locais exigem confirmação quando aplicável.",
                 bg=PANEL, fg=CYAN).pack(padx=16, pady=12)
        actions = [
            ("Abrir Calculadora", lambda: self.open_app("calc.exe", "Calculadora")),
            ("Abrir Visual Studio Code", self.open_vscode_dialog),
            ("Abrir Bloco de Notas", lambda: self.open_app("notepad.exe", "Bloco de Notas")),
            ("Abrir navegador", self.open_browser),
            ("Pesquisar na web", self.web_search),
            ("Criar projeto", self.new_project),
            ("Auditar pasta local", self.audit_local),
            ("Capturar tela", self.screen_capture),
            ("Capturar e ler texto (OCR)", self.capture_and_ocr),
            ("Memória local", self.manage_memory),
            ("Abrir pasta de projetos", self.open_projects_folder)
        ]
        for label, action in actions:
            self.button(win, label, action, compact=True).pack(fill="x", padx=16, pady=4)

    def extract_workspace_action(self, answer):
        """Extract a strictly structured project manifest from an AI response."""
        match = re.search(
            r"\[\[JARVIS_WORKSPACE_ACTION\]\](.*?)\[\[/JARVIS_WORKSPACE_ACTION\]\]",
            answer or "", flags=re.S
        )
        if not match:
            return None
        try:
            payload = json.loads(match.group(1).strip())
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or set(payload) != {"name", "files"}:
            return None
        return payload

    def apply_workspace_action(self, action):
        name = action.get("name", "projeto")
        files = action.get("files", [])
        count = len(files) if isinstance(files, list) else 0
        if not messagebox.askyesno(
            "Confirmar criação do projeto",
            f"O JARVIS preparou {count} arquivo(s) para o projeto '{name}'.\n"
            "Os arquivos serão gravados somente na pasta de projetos do JARVIS. "
            "Nenhum código será executado. Deseja continuar?"
        ):
            self.add("PROJETOS", "Criação cancelada; nenhum arquivo foi gravado.")
            return
        try:
            project_path, written = create_generated_project(name, files)
            self.add("PROJETOS", f"Projeto criado em {project_path} ({len(written)} arquivo(s)).")
            if messagebox.askyesno(
                "Abrir no VS Code",
                f"Projeto salvo. Deseja abrir '{name}' no Visual Studio Code?"
            ):
                try:
                    open_in_vscode(project_path)
                    self.add("CONTROLE", f"VS Code aberto no projeto {name}.")
                except Exception as exc:
                    self.add("CONTROLE", f"Projeto salvo, mas não consegui abrir o VS Code: {exc}", True)
        except Exception as exc:
            self.add("PROJETOS", f"Não foi possível criar o projeto: {exc}", True)
            messagebox.showerror("Projeto", str(exc))

    def open_vscode_dialog(self):
        if not messagebox.askyesno(
            "Abrir Visual Studio Code",
            "Permitir que o JARVIS abra o VS Code na pasta de projetos?"
        ):
            return
        try:
            open_in_vscode()
            self.add("CONTROLE", "Visual Studio Code aberto na pasta de projetos.")
        except Exception as exc:
            messagebox.showerror("Visual Studio Code", str(exc))
            self.add("CONTROLE", str(exc), True)

    def try_vscode_command(self, prompt):
        text = prompt.strip()
        if not re.match(
            r"^(?:jarvis[, ]*)?(?:abra|abrir|abre|inicie|iniciar)\s+(?:o\s+)?(?:visual\s+studio\s+code|vs\s*code)$",
            text, re.I
        ):
            return False
        self.open_vscode_dialog()
        return True

    def open_app(self, exe, label):
        if not messagebox.askyesno("Autorizar ação", f"Permitir abrir {label}?"):
            return
        try:
            subprocess.Popen([exe], shell=False)
            self.add("CONTROLE", label + " aberto.")
        except Exception as exc:
            messagebox.showerror("Controle", str(exc))

    def try_reminder_command(self, prompt):
        parsed = parse_reminder(prompt)
        if not parsed:
            return False
        title, when = parsed
        if when <= datetime.now():
            self.add("JARVIS", "Esse horário já passou. Informe um horário futuro.")
            return True
        notify_time = when - timedelta(minutes=10)
        if not messagebox.askyesno(
            "Confirmar lembrete",
            f"Compromisso: {title}\nHorário: {when.strftime('%d/%m/%Y às %H:%M')}\n\n"
            f"Vou avisar às {notify_time.strftime('%H:%M')}, exatamente 10 minutos antes. Confirmar?"
        ):
            self.add("JARVIS", "Lembrete não criado.")
            return True
        self.reminders.add(title, when)
        self.add("JARVIS", f"Lembrete salvo: {title}, às {when.strftime('%d/%m/%Y %H:%M')}. "
                           "Vou notificar 10 minutos antes. O JARVIS precisa estar aberto no Windows.")
        return True

    def _check_reminders(self):
        for item in self.reminders.due():
            event_time = datetime.fromisoformat(item["when"])
            body = f"{item.get('title', 'Compromisso')} — às {event_time.strftime('%H:%M')}"
            if Notification is not None:
                try:
                    toast = Notification(app_id="JARVIS", title="Lembrete do JARVIS", msg=body, duration="long")
                    if audio is not None:
                        toast.set_audio(audio.Default, loop=False)
                    toast.show()
                    self.add("LEMBRETE", body)
                    continue
                except Exception:
                    pass
            self.root.after(0, lambda b=body: messagebox.showinfo("Lembrete do JARVIS", b))
            self.add("LEMBRETE", body)

    def open_reminders(self):
        win = tk.Toplevel(self.root)
        win.title("Lembretes do JARVIS")
        win.configure(bg=PANEL)
        win.geometry("520x420")
        tk.Label(win, text="COMPROMISSOS AGENDADOS", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=14)
        frame = tk.Frame(win, bg=PANEL)
        frame.pack(fill="both", expand=True, padx=16)
        items = self.reminders.upcoming(30)
        if not items:
            tk.Label(frame, text="Nenhum compromisso futuro.", bg=PANEL, fg=MUTED).pack(anchor="w")
        for item in items:
            when = datetime.fromisoformat(item["when"])
            row = tk.Frame(frame, bg=CARD, padx=10, pady=8)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=f"{when.strftime('%d/%m/%Y %H:%M')}  •  {item['title']}",
                     bg=CARD, fg=TEXT, anchor="w").pack(side="left", fill="x", expand=True)
            tk.Button(row, text="Cancelar", command=lambda rid=item["id"], w=row: self._cancel_reminder(rid, w),
                      bg="#512331", fg=TEXT, relief="flat").pack(side="right")
        tk.Label(win, text="Todos os avisos são programados para 10 minutos antes.\n"
                          "No EXE, mantenha o JARVIS aberto para o monitor de lembretes funcionar.",
                 bg=PANEL, fg=MUTED, justify="left").pack(anchor="w", padx=16, pady=12)

    def _cancel_reminder(self, reminder_id, row):
        if self.reminders.cancel(reminder_id):
            row.destroy()
            self.add("LEMBRETE", "Compromisso cancelado.")

    def try_browser_command(self, prompt):
        """Handle explicit, low-risk open/search requests in the JARVIS browser."""
        text = prompt.strip()
        video = re.match(r"^(?:jarvis[, ]*)?(?:abra|abrir|abre|mostre|mostrar)\s+(?:um\s+)?(?:vídeo|video)\s+(?:sobre\s+|de\s+|do\s+|da\s+)?(.+)$", text, re.I)
        if video:
            query = video.group(1).strip(" .!?")
            self.open_internal_url("https://www.youtube.com/results?search_query=" + quote_plus(query), "VÍDEO")
            self.add("JARVIS", "Encontrei a pesquisa de vídeos no YouTube. O resultado será exibido na janela interna; escolha o vídeo que deseja reproduzir.")
            return True
        site = re.match(r"^(?:jarvis[, ]*)?(?:abra|abrir|abre|acesse|acessar)\s+(?:o\s+)?(?:site\s+)?(https?://\S+|[\w.-]+\.[a-z]{2,}(?:/\S*)?)$", text, re.I)
        if site:
            self.open_internal_url(site.group(1), "NAVEGADOR")
            return True
        if re.match(r"^(?:jarvis[, ]*)?(?:abra|abrir|abre)\s+(?:o\s+)?(?:youtube|you tube)$", text, re.I):
            self.open_internal_url("https://www.youtube.com", "VÍDEO")
            return True
        search = re.match(r"^(?:jarvis[, ]*)?(?:pesquise|pesquisar|procure|buscar)\s+(?:na internet\s+)?(.+)$", text, re.I)
        weather = re.match(r"^(?:jarvis[, ]*)?(?:qual|como está|como esta|me diga)\s+(?:o\s+)?(?:clima|tempo|previsão do tempo|previsao do tempo)(?:\s+(?:em|de|para)\s+(.+))?$", text, re.I)
        query = search.group(1).strip() if search else ("clima e previsão atual " + (weather.group(1) or "").strip() if weather else "")
        if query:
            tavily_key = keyring.get_password("JARVIS", "tavily_key") or ""
            if tavily_key:
                self.add("PESQUISA", "Consultando a web com Tavily…")
                threading.Thread(target=self._run_tavily_search, args=(query, tavily_key), daemon=True).start()
            else:
                self.open_internal_url("https://www.google.com/search?q=" + quote_plus(query), "PESQUISA")
                self.add("JARVIS", "Tavily não configurada. Abri a pesquisa do Google no navegador interno.")
            return True
        return False

    def _run_tavily_search(self, query, api_key):
        try:
            data = tavily_search(api_key, query, max_results=5)
            lines = [data.get("answer") or "A pesquisa retornou estes resultados:", ""]
            for item in data["results"]:
                lines.extend([item["title"], item["content"], item["url"], ""])
            rendered = "\n".join(lines)[:6500]
            self.root.after(0, lambda value=rendered: self.add("PESQUISA • TAVILY", value))
        except Exception as exc:
            message = str(exc)
            self.root.after(0, lambda value=message: self.add("PESQUISA • ERRO", value, True))

    def open_internal_url(self, url, label="NAVEGADOR"):
        try:
            if self.internal_browser is None or self.internal_browser.window is None:
                self.internal_browser = InternalBrowser(self.root, url)
            else:
                self.internal_browser.navigate(url)
            self.add(label, "Página solicitada na janela do navegador interno do JARVIS.")
        except Exception as exc:
            messagebox.showerror("Navegador JARVIS", str(exc))

    def open_browser(self):
        if messagebox.askyesno("Navegador JARVIS", "Abrir o navegador dentro do JARVIS?"):
            self.open_internal_url("https://www.google.com")

    def web_search(self):
        query = simpledialog.askstring("Pesquisa na web", "O que deseja pesquisar?")
        if query and messagebox.askyesno("Confirmar pesquisa", "Pesquisar dentro do JARVIS: " + query + "?"):
            self.open_internal_url("https://www.google.com/search?q=" + quote_plus(query), "PESQUISA")

    def open_video(self):
        query = simpledialog.askstring("Vídeo", "Qual vídeo deseja assistir?")
        if query and messagebox.askyesno("Abrir vídeo", "Pesquisar este vídeo no YouTube dentro do JARVIS?\n" + query):
            self.open_internal_url("https://www.youtube.com/results?search_query=" + quote_plus(query), "VÍDEO")

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
        token = keyring.get_password("JARVIS", "brapi_key") or ""
        MoneyLab(self.root, api_key=token)
        self.add("JARVIS MONEY", "Painel de análise aberto. Consulta brapi disponível quando o token estiver configurado.")

    def drive(self):
        destination = simpledialog.askstring("JARVIS DRIVE", "Destino para abrir no mapa:")
        if not destination:
            return
        if messagebox.askyesno("Abrir navegação", f"Abrir rota até {destination} no navegador?"):
            url = "https://www.google.com/maps/dir/?api=1&destination=" + quote_plus(destination)
            self.open_internal_url(url, "JARVIS DRIVE")
            self.add("JARVIS DRIVE", "Rota aberta no navegador interno. O JARVIS não controla o veículo nem confirma sua localização atual.")

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


    def try_memory_command(self, prompt):
        text = prompt.strip()
        remember = re.match(r"^(?:jarvis[, ]*)?(?:lembre(?:-se)?(?: de)?|guarde(?: que)?|memorize(?: que)?)\s+(.+)$", text, re.I)
        if remember:
            fact = remember.group(1).strip().rstrip(".!?")
            try:
                saved = self.memory.remember(fact)
                self.add("MEMÓRIA LOCAL", "Lembrei: " + saved)
            except Exception as exc:
                self.add("MEMÓRIA LOCAL", str(exc), True)
            return True
        if re.search(r"\b(o que você lembra|o que voce lembra|minhas memórias|minhas memorias|listar memórias|listar memorias)\b", text, re.I):
            items = self.memory.list()
            if not items:
                self.add("MEMÓRIA LOCAL", "Ainda não há fatos salvos.")
            else:
                self.add("MEMÓRIA LOCAL", "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1)))
            return True
        if re.search(r"\b(esqueça tudo|esqueca tudo|apague minhas memórias|apague minhas memorias|limpe a memória|limpe a memoria)\b", text, re.I):
            if messagebox.askyesno("Apagar memória local", "Apagar todos os fatos salvos neste computador?"):
                count = self.memory.forget()
                self.add("MEMÓRIA LOCAL", f"{count} fato(s) apagado(s).")
            else:
                self.add("MEMÓRIA LOCAL", "Nenhuma memória foi apagada.")
            return True
        return False

    def manage_memory(self):
        win = tk.Toplevel(self.root)
        win.title("Memória local — JARVIS")
        win.configure(bg=PANEL)
        win.geometry("640x520")
        tk.Label(win, text="FATOS SALVOS NESTE COMPUTADOR", bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=12)
        listing = tk.Listbox(win, bg="#041321", fg=TEXT, selectbackground="#075d85",
                             relief="flat", font=("Segoe UI", 10), height=15)
        listing.pack(fill="both", expand=True, padx=14, pady=6)
        def refresh():
            listing.delete(0, "end")
            for item in self.memory.list():
                listing.insert("end", item)
        def remove_selected():
            selected = listing.curselection()
            if not selected:
                messagebox.showinfo("Memória", "Selecione um fato para apagar.", parent=win)
                return
            self.memory.forget(selected[0] + 1)
            refresh()
        def clear_all():
            if messagebox.askyesno("Apagar memória", "Apagar todos os fatos locais?", parent=win):
                self.memory.forget()
                refresh()
        actions = tk.Frame(win, bg=PANEL)
        actions.pack(fill="x", padx=14, pady=10)
        self.button(actions, "APAGAR SELECIONADO", remove_selected, compact=True).pack(side="left", padx=3)
        self.button(actions, "APAGAR TUDO", clear_all, compact=True).pack(side="left", padx=3)
        tk.Label(win, text="A memória é local, não sincroniza e só guarda fatos pedidos explicitamente.",
                 bg=PANEL, fg=MUTED, wraplength=580, justify="left").pack(anchor="w", padx=14, pady=(0, 12))
        refresh()

    def capture_and_ocr(self):
        if not messagebox.askyesno("Visão e OCR", "Autoriza capturar a tela atual e extrair texto localmente?"):
            return
        source = filedialog.asksaveasfilename(
            title="Salvar captura para OCR", defaultextension=".png",
            filetypes=[("Imagem PNG", "*.png")])
        if not source:
            return
        try:
            capture_screen(source)
            extracted = read_screen_text(source).strip()
            if not extracted:
                self.add("VISÃO / OCR", "A captura foi feita, mas nenhum texto legível foi encontrado.")
                return
            self.add("VISÃO / OCR", extracted[:6000])
            self.history.append({"role": "user", "content": "Texto extraído da captura de tela autorizada (OCR local):\n" + extracted[:6000]})
            self.agent_var.set("Visão")
        except Exception as exc:
            messagebox.showerror("Visão / OCR", str(exc))

    def close(self):
        self.voice_stop_event.set()
        self.voice_resume_event.set()
        self.root.destroy()


def main():
    root = tk.Tk()
    JarvisApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
