import json, os, subprocess, threading, urllib.request, urllib.error, webbrowser, keyring
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from pathlib import Path
from urllib.parse import quote_plus
from desktop_tools import capture_screen
from project_workspace import create_project
from defensive_audit import audit_folder

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
        CONFIG_FILE.write_text(json.dumps(self.config,ensure_ascii=False,indent=2),encoding="utf-8")

    def build(self):
        self.root.configure(bg="#07111d")
        top=tk.Frame(self.root,bg="#0b1d2c",padx=16,pady=12); top.pack(fill="x")
        tk.Label(top,text="J.A.R.V.I.S",fg="#55dfff",bg="#0b1d2c",font=("Segoe UI",19,"bold")).pack(side="left")
        ttk.Button(top,text="Configurações",command=self.settings).pack(side="right")
        ttk.Button(top,text="Ferramentas",command=self.tools).pack(side="right",padx=8)
        self.chat=tk.Text(self.root,bg="#091725",fg="#e6f7ff",insertbackground="white",wrap="word",
                          font=("Segoe UI",11),relief="flat",padx=14,pady=14,state="disabled")
        self.chat.pack(fill="both",expand=True,padx=14,pady=14)
        self.chat.tag_configure("speaker",foreground="#55dfff",font=("Segoe UI",10,"bold"))
        self.status=tk.StringVar(value="PRONTO")
        tk.Label(self.root,textvariable=self.status,bg="#07111d",fg="#55dfff",anchor="w",padx=16).pack(fill="x")
        bar=tk.Frame(self.root,bg="#0b1d2c",padx=12,pady=12); bar.pack(fill="x",padx=14,pady=(4,14))
        self.entry=tk.Entry(bar,bg="#10283a",fg="white",insertbackground="white",relief="flat",font=("Segoe UI",11))
        self.entry.pack(side="left",fill="x",expand=True,ipady=10,padx=(0,8)); self.entry.bind("<Return>",lambda e:self.send())
        ttk.Button(bar,text="Enviar",command=self.send).pack(side="right")

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
        ttk.Button(w,text="Modo Hacker defensivo",command=self.defensive).pack(fill="x",padx=18,pady=5)
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
