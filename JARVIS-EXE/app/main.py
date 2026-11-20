import json, os, subprocess, threading, urllib.request, urllib.error, webbrowser, keyring
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
from urllib.parse import quote_plus
from desktop_tools import capture_screen
from project_workspace import create_project
from defensive_audit import audit_folder
from hologram_lab import HologramLab
from money_lab import MoneyLab
from security_lab import SecurityLab

APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "Jarvis"
CONFIG_FILE = APP_DIR / "settings.json"
SYSTEM = ("Você é o JARVIS, assistente em português do Brasil. Seja claro e honesto. "
         "Nunca afirme que executou algo sem confirmação. Peça autorização para ações no computador.")

class JarvisApp:
    def __init__(self, root):
        self.root=root; root.title("JARVIS — Assistente para Windows"); root.geometry("900x660"); root.minsize(700,500)
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.config=self.load_config(); self.history=[{"role":"system","content":SYSTEM}]; self.busy=False
        self.build(); self.add("JARVIS","Sistema iniciado. Configure sua API para conversar.")

    def load_config(self):
        try:
            d=json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return {"endpoint":d.get("endpoint","https://api.groq.com/openai/v1/chat/completions"),
                    "model":d.get("model","openai/gpt-oss-120b"),"api_key":keyring.get_password("JARVIS","api_key") or ""}
        except Exception: return {"endpoint":"https://api.groq.com/openai/v1/chat/completions","model":"openai/gpt-oss-120b","api_key":""}

    def save_config(self):
        # API credentials belong only in the OS keyring, never in settings.json.
        safe_config = {key: value for key, value in self.config.items() if key != "api_key"}
        CONFIG_FILE.write_text(json.dumps(safe_config,ensure_ascii=False,indent=2),encoding="utf-8")

    def _styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Jarvis.TButton", background="#12344c", foreground="#e8f6ff",
                        padding=(12, 9), borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Jarvis.TButton", background=[("active", "#18516d")],
                  foreground=[("disabled", "#7895a8")])
        style.configure("Accent.TButton", background="#087da3", foreground="#ffffff",
                        padding=(14, 10), borderwidth=0, font=("Segoe UI", 9, "bold"))
        style.map("Accent.TButton", background=[("active", "#0a9bc7")])
        style.configure("Jarvis.TEntry", fieldbackground="#10283a", foreground="#ffffff",
                        insertcolor="#ffffff", padding=10, borderwidth=0)

    def build(self):
        self.root.configure(bg="#07111f")
        self._styles()
        header = tk.Frame(self.root, bg="#0b1d2e", padx=20, pady=15)
        header.pack(fill="x")
        brand = tk.Frame(header, bg="#0b1d2e")
        brand.pack(side="left")
        tk.Label(brand, text="J.A.R.V.I.S", fg="#48dcff", bg="#0b1d2e",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(brand, text="PERSONAL INTELLIGENCE SYSTEM", fg="#8baabd",
                 bg="#0b1d2e", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Button(header, text="Configurações", style="Jarvis.TButton",
                   command=self.settings).pack(side="right")
        ttk.Button(header, text="Ferramentas", style="Jarvis.TButton",
                   command=self.tools).pack(side="right", padx=8)

        shell = tk.Frame(self.root, bg="#07111f")
        shell.pack(fill="both", expand=True, padx=14, pady=14)
        sidebar = tk.Frame(shell, bg="#0b1d2e", width=190, padx=12, pady=14)
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="MÓDULOS", bg="#0b1d2e", fg="#7899ad",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=4, pady=(2, 10))
        ttk.Button(sidebar, text="⌂  Conversa", style="Accent.TButton",
                   command=lambda: self.entry.focus_set()).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="◇  Hologramas 3D", style="Jarvis.TButton",
                   command=self.open_hologram_lab).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="▥  JARVIS MONEY", style="Jarvis.TButton",
                   command=self.open_money_lab).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="➤  JARVIS DRIVE", style="Jarvis.TButton",
                   command=self.drive_planned).pack(fill="x", pady=4)
        ttk.Button(sidebar, text="⌘  SECURITY LAB", style="Jarvis.TButton",
                   command=self.open_security_lab).pack(fill="x", pady=4)
        tk.Frame(sidebar, bg="#1b3a50", height=1).pack(fill="x", pady=14)
        tk.Label(sidebar, text="ESTADO DO SISTEMA", bg="#0b1d2e", fg="#7899ad",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=4)
        self.status = tk.StringVar(value="PRONTO")
        tk.Label(sidebar, textvariable=self.status, bg="#0b1d2e", fg="#48dcff",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=4, pady=(7, 2))
        tk.Label(sidebar, text="Paleta azul-marinho e ciano",
                 bg="#0b1d2e", fg="#7899ad", font=("Segoe UI", 7),
                 wraplength=155, justify="left").pack(anchor="w", padx=4, pady=(8, 0))

        content = tk.Frame(shell, bg="#07111f")
        content.pack(side="left", fill="both", expand=True)
        intro = tk.Frame(content, bg="#0c2032", padx=16, pady=12)
        intro.pack(fill="x", pady=(0, 10))
        tk.Label(intro, text="CENTRAL DE COMANDO", bg="#0c2032", fg="#48dcff",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(intro, text="Converse com o JARVIS ou abra um dos módulos disponíveis.",
                 bg="#0c2032", fg="#b6cad8", font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 0))

        chat_panel = tk.Frame(content, bg="#091827", highlightthickness=1,
                              highlightbackground="#183b53")
        chat_panel.pack(fill="both", expand=True)
        self.chat = tk.Text(chat_panel, bg="#091827", fg="#e8f6ff",
                            insertbackground="#ffffff", wrap="word",
                            font=("Segoe UI", 10), relief="flat", padx=16, pady=16,
                            state="disabled", borderwidth=0)
        self.chat.pack(fill="both", expand=True, padx=2, pady=2)
        self.chat.tag_configure("speaker", foreground="#48dcff",
                                font=("Segoe UI", 9, "bold"))
        bar = tk.Frame(content, bg="#0b1d2e", padx=12, pady=12)
        bar.pack(fill="x", pady=(10, 0))
        self.entry = ttk.Entry(bar, style="Jarvis.TEntry")
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry.bind("<Return>", lambda e: self.send())
        ttk.Button(bar, text="Enviar", style="Accent.TButton",
                   command=self.send).pack(side="right")

    def add(self,who,msg):
        self.chat.configure(state="normal"); self.chat.insert("end",who+"\n","speaker")
        self.chat.insert("end",msg+"\n\n"); self.chat.see("end"); self.chat.configure(state="disabled")

    def settings(self):
        w=tk.Toplevel(self.root); w.title("Configurações da IA"); w.configure(bg="#0b1d2c"); fields={}
        for label,key,secret in [("Endpoint completo","endpoint",False),("Modelo","model",False),("Chave da API","api_key",True)]:
            tk.Label(w,text=label,bg="#0b1d2c",fg="white").pack(anchor="w",padx=14,pady=(10,2))
            e=tk.Entry(w,width=64,show="*" if secret else None); e.insert(0,self.config.get(key,"")); e.pack(padx=14); fields[key]=e
        tk.Label(w,text="Use HTTPS. Nunca compartilhe sua chave.",bg="#0b1d2c",fg="#9bb8c9").pack(padx=14,pady=8)
        def save():
            self.config.update({k:e.get().strip() for k,e in fields.items() if k!="api_key"})
            keyring.set_password("JARVIS","api_key",fields["api_key"].get().strip())
            self.save_config(); w.destroy(); self.add("JARVIS","Configurações salvas no perfil local.")
        ttk.Button(w,text="Salvar",command=save).pack(pady=12)

    def send(self):
        prompt=self.entry.get().strip()
        if not prompt or self.busy:return
        self.entry.delete(0,"end"); self.add("VOCÊ",prompt); self.history.append({"role":"user","content":prompt})
        self.busy=True; self.status.set("PROCESSANDO"); threading.Thread(target=self.ask,daemon=True).start()

    def ask(self):
        try:
            ep=self.config["endpoint"]; key=keyring.get_password("JARVIS","api_key") or ""; model=self.config["model"]
            if not ep.startswith("https://"): raise ValueError("O endpoint remoto precisa usar HTTPS.")
            if not key or not model: raise ValueError("Configure modelo e chave da API.")
            body=json.dumps({"model":model,"messages":self.history[-24:],"stream":False}).encode()
            req=urllib.request.Request(ep,data=body,headers={"Content-Type":"application/json","Authorization":"Bearer "+key},method="POST")
            with urllib.request.urlopen(req,timeout=45) as r: data=json.loads(r.read().decode("utf-8"))
            answer=data["choices"][0]["message"]["content"]
            if isinstance(answer,list): answer="\n".join(x.get("text","") for x in answer if isinstance(x,dict))
            if not isinstance(answer,str) or not answer.strip(): raise ValueError("Resposta vazia ou formato inesperado.")
            self.history.append({"role":"assistant","content":answer})
            self.root.after(0,lambda:self.add("JARVIS",answer)); self.root.after(0,lambda:self.status.set("ONLINE"))
        except urllib.error.HTTPError as e:
            detail=e.read(1000).decode("utf-8","replace")
            self.root.after(0,lambda:self.add("ERRO",f"HTTP {e.code}: {detail}")); self.root.after(0,lambda:self.status.set("ERRO"))
        except Exception as e:
            msg=str(e); self.root.after(0,lambda:self.add("ERRO",msg)); self.root.after(0,lambda:self.status.set("ERRO"))
        finally:self.busy=False

    def tools(self):
        w=tk.Toplevel(self.root); w.title("Ferramentas do computador"); w.configure(bg="#0b1d2c")
        tk.Label(w,text="Cada ação abaixo exige confirmação",bg="#0b1d2c",fg="#55dfff").pack(padx=14,pady=12)
        for label,exe in [("Abrir Bloco de Notas","notepad.exe"),("Abrir Calculadora","calc.exe")]:
            ttk.Button(w,text=label,command=lambda x=exe,l=label:self.open_app(x,l)).pack(fill="x",padx=18,pady=5)
        ttk.Button(w,text="Abrir navegador",command=self.open_browser).pack(fill="x",padx=18,pady=5)
        ttk.Button(w,text="Pesquisar na web",command=self.web_search).pack(fill="x",padx=18,pady=5)
        ttk.Button(w,text="Criar projeto de código",command=self.new_project).pack(fill="x",padx=18,pady=5)
        ttk.Button(w,text="Auditar pasta local (defensivo)",command=self.audit_local).pack(fill="x",padx=18,pady=5)
        ttk.Button(w,text="Capturar tela (sob comando)",command=self.screen_capture).pack(fill="x",padx=18,pady=5)
        ttk.Button(w,text="Laboratório de hologramas 3D",command=self.open_hologram_lab).pack(fill="x",padx=18,pady=5)
        ttk.Button(w,text="JARVIS Security Lab (Blue/Red Team)",command=self.open_security_lab).pack(fill="x",padx=18,pady=5)
        tk.Label(w,text="Controle genérico do mouse, leitura de tela e varreduras não estão habilitados nesta versão.",
                 bg="#0b1d2c",fg="#a9bdca",wraplength=390).pack(padx=18,pady=12)

    def open_app(self,exe,label):
        if messagebox.askyesno("Autorizar ação",f"Permitir abrir {label}?"):
            try: subprocess.Popen([exe],shell=False); self.add("FERRAMENTA",label+" aberto.")
            except Exception as e:self.add("ERRO",str(e))

    def open_browser(self):
        if messagebox.askyesno("Autorizar ação","Abrir o navegador padrão?"):
            webbrowser.open("https://www.google.com"); self.add("FERRAMENTA","Solicitação enviada ao navegador.")

    def web_search(self):
        q=simpledialog.askstring("Pesquisa na web","O que deseja pesquisar?")
        if q and messagebox.askyesno("Autorizar pesquisa","Pesquisar: "+q+"?"):
            webbrowser.open("https://www.google.com/search?q="+quote_plus(q)); self.add("FERRAMENTA","Pesquisa aberta; resultados não foram lidos.")

    def new_project(self):
        name=simpledialog.askstring("Novo projeto","Nome do projeto (letras, números, _ ou -):")
        if not name:return
        try:
            path=create_project(name)
            self.add("PROJETOS",f"Pasta criada: {path}. Código não é executado automaticamente.")
        except Exception as e:messagebox.showerror("Projeto",str(e))

    def audit_local(self):
        folder=filedialog.askdirectory(title="Selecione uma pasta sua para revisão defensiva")
        if not folder:return
        if not messagebox.askyesno("Confirmar auditoria","Analisar arquivos desta pasta localmente?"):return
        try:
            findings=audit_folder(folder)
            self.add("AUDITORIA",f"{len(findings)} ocorrências para revisão manual; isso não prova vulnerabilidade.")
            for item in findings[:30]:
                self.add("ACHADO",f"{item['file']}:{item['line']} — {item['pattern']}")
        except Exception as e:messagebox.showerror("Auditoria",str(e))

    def open_hologram_lab(self):
        HologramLab(self.root)
        self.add("HOLOGRAMAS","Laboratório 3D aberto. A câmera permanece desligada até você ativá-la.")

    def open_security_lab(self):
        SecurityLab(self.root, on_report=lambda mode, report:
                    self.add(mode, report))
        self.add("SECURITY LAB",
                 "Perfis Blue Team e Red Team educativo disponíveis. Red Team opera apenas em cenários fictícios locais.")

    def open_money_lab(self):
        MoneyLab(self.root)
        self.add("JARVIS MONEY",
                 "Painel de análise aberto. Dados de mercado ainda não estão conectados; nenhuma operação real é executada.")

    def drive_planned(self):
        messagebox.showinfo("JARVIS DRIVE",
            "Módulo planejado: localização autorizada, mapas, trânsito e abertura de navegação. "
            "Esta versão ainda não controla veículos.")
        self.add("JARVIS DRIVE", "Módulo em planejamento; nenhum veículo é controlado.")

    def screen_capture(self):
        if not messagebox.askyesno("Captura de tela","Autoriza capturar a tela atual?"):return
        dest=filedialog.asksaveasfilename(defaultextension=".png",filetypes=[("PNG","*.png")])
        if not dest:return
        try:
            capture_screen(dest)
            self.add("VISÃO",f"Captura salva em {dest}.")
        except Exception as e:messagebox.showerror("Captura",str(e))

    def defensive(self):
        messagebox.showinfo("Modo Hacker defensivo","Esta versão é informativa. Auditorias futuras exigirão propriedade/autorização, escopo definido e ambiente de teste. Não há invasão, coleta de credenciais ou extração de dados.")
        self.add("MODO HACKER","Orientação defensiva aberta. Nenhuma varredura foi executada.")

if __name__=="__main__":
    root=tk.Tk(); JarvisApp(root); root.mainloop()
