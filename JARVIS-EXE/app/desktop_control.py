"""User-visible Windows desktop controls for JARVIS EXE.

This module offers explicit, foreground actions only. It never uses a shell,
requests administrator elevation, hides activity, or bypasses Windows policy.
"""
import os
import re
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
from python_environment import (
    EnvironmentInstallError,
    install_package_in_project,
    resolve_python_launcher,
    validate_package_name,
    validate_project_venv,
)

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    import psutil
except Exception:
    psutil = None


_SAFE_HOTKEYS = {
    "ctrl+c": ("ctrl", "c"),
    "ctrl+v": ("ctrl", "v"),
    "ctrl+x": ("ctrl", "x"),
    "ctrl+a": ("ctrl", "a"),
    "ctrl+s": ("ctrl", "s"),
    "ctrl+f": ("ctrl", "f"),
    "ctrl+z": ("ctrl", "z"),
    "ctrl+y": ("ctrl", "y"),
    "ctrl+l": ("ctrl", "l"),
    "alt+tab": ("alt", "tab"),
    "win+d": ("win", "d"),
}
_BLOCKED_PROCESSES = {
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "winlogon.exe",
}


class DesktopControlWindow:
    """A foreground control panel; each action is confirmed and audited."""

    def __init__(self, parent, authorize, on_log):
        self.authorize = authorize
        self.on_log = on_log
        self.window = tk.Toplevel(parent)
        self.window.title("JARVIS — Controle do Windows")
        self.window.geometry("720x760")
        self.window.minsize(620, 620)
        self.window.configure(bg="#071827")
        self._build()

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg="#071827", fg="#eaf8ff",
                 anchor="w", justify="left", wraplength=660).pack(fill="x", padx=14, pady=4)

    def _button(self, parent, text, command):
        tk.Button(parent, text=text, command=command, bg="#0b2b43", fg="#eaf8ff",
                  activebackground="#124361", activeforeground="white",
                  relief="flat", padx=12, pady=7).pack(fill="x", padx=14, pady=3)

    def _build(self):
        tk.Label(self.window, text="CONTROLE OPERACIONAL DO WINDOWS",
                 bg="#071827", fg="#39d9ff",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
        self._label(
            self.window,
            "As ações acontecem visivelmente na sessão atual. O JARVIS não eleva privilégios, "
            "não desativa proteções e não executa comandos arbitrários. Confirme cada ação."
        )
        self._button(self.window, "Abrir aplicativo ou arquivo executável escolhido…", self.open_program)
        self._button(self.window, "Abrir arquivo ou pasta…", self.open_path)
        self._button(self.window, "Abrir Configurações do Windows", self.open_settings)
        self._button(self.window, "Abrir Gerenciador de Tarefas", self.open_task_manager)
        self._button(self.window, "Copiar ou mover arquivos…", self.copy_or_move)
        self._button(self.window, "Instalar pacote no ambiente Python do projeto…", self.install_python_package)
        self._button(self.window, "Instalar aplicativo pelo WinGet…", self.install_windows_package)

        tk.Label(self.window, text="MOUSE E TECLADO", bg="#071827", fg="#39d9ff",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(14, 2))
        row = tk.Frame(self.window, bg="#071827")
        row.pack(fill="x", padx=14)
        self.x_entry = tk.Entry(row, width=7)
        self.y_entry = tk.Entry(row, width=7)
        for label, entry in (("X", self.x_entry), ("Y", self.y_entry)):
            tk.Label(row, text=label, bg="#071827", fg="#eaf8ff").pack(side="left")
            entry.pack(side="left", padx=(3, 10))
        tk.Button(row, text="Clicar", command=self.click, bg="#0b2b43", fg="#eaf8ff",
                  relief="flat").pack(side="left", padx=4)
        self._button(self.window, "Digitar texto na janela em foco…", self.type_text)
        self._button(self.window, "Enviar atalho seguro…", self.hotkey)

        tk.Label(self.window, text="PROCESSOS EM EXECUÇÃO", bg="#071827", fg="#39d9ff",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(14, 2))
        process_row = tk.Frame(self.window, bg="#071827")
        process_row.pack(fill="both", expand=True, padx=14, pady=(2, 12))
        self.processes = tk.Listbox(process_row, bg="#041321", fg="#eaf8ff",
                                    selectbackground="#075d85", height=8)
        self.processes.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(process_row, command=self.processes.yview)
        scrollbar.pack(side="right", fill="y")
        self.processes.configure(yscrollcommand=scrollbar.set)
        controls = tk.Frame(self.window, bg="#071827")
        controls.pack(fill="x", padx=14, pady=(0, 14))
        tk.Button(controls, text="Atualizar lista", command=self.refresh_processes,
                  bg="#0b2b43", fg="#eaf8ff", relief="flat").pack(side="left", padx=3)
        tk.Button(controls, text="Encerrar processo selecionado…", command=self.terminate_process,
                  bg="#63313b", fg="#fff", relief="flat").pack(side="left", padx=3)
        self.refresh_processes()

    def _confirm(self, title, message):
        return messagebox.askyesno(title, message, parent=self.window)

    def open_program(self):
        if not self.authorize("launch_app"):
            return
        path = filedialog.askopenfilename(
            parent=self.window, title="Escolha um programa",
            filetypes=[("Programas", "*.exe"), ("Todos os arquivos", "*.*")]
        )
        if not path:
            return
        target = Path(path).resolve()
        if target.suffix.lower() != ".exe" or not target.is_file():
            messagebox.showwarning("Programa inválido", "Escolha um executável .exe existente.", parent=self.window)
            return
        if not self._confirm("Abrir programa", f"Permitir abrir este programa?\n{target.name}\n\n{target}"):
            return
        try:
            subprocess.Popen([str(target)], shell=False, cwd=str(target.parent))
            self.on_log("Programa iniciado: " + target.name)
        except Exception as exc:
            messagebox.showerror("Não foi possível abrir", str(exc), parent=self.window)

    def open_path(self):
        if not self.authorize("workspace_open"):
            return
        path = filedialog.askopenfilename(parent=self.window, title="Escolha um arquivo")
        if not path:
            path = filedialog.askdirectory(parent=self.window, title="Ou escolha uma pasta")
        if not path:
            return
        target = Path(path).resolve()
        if not self._confirm("Abrir item", f"Abrir este item no Windows?\n{target.name}"):
            return
        try:
            os.startfile(str(target))
            self.on_log("Item aberto: " + target.name)
        except Exception as exc:
            messagebox.showerror("Não foi possível abrir", str(exc), parent=self.window)

    def open_settings(self):
        if not self.authorize("system_settings"):
            return
        if self._confirm("Configurações do Windows", "Abrir as Configurações do Windows?"):
            try:
                os.startfile("ms-settings:")
                self.on_log("Configurações do Windows abertas.")
            except Exception as exc:
                messagebox.showerror("Configurações", str(exc), parent=self.window)

    def open_task_manager(self):
        if not self.authorize("system_settings"):
            return
        if self._confirm("Gerenciador de Tarefas", "Abrir o Gerenciador de Tarefas?"):
            try:
                subprocess.Popen(["taskmgr.exe"], shell=False)
                self.on_log("Gerenciador de Tarefas aberto.")
            except Exception as exc:
                messagebox.showerror("Gerenciador de Tarefas", str(exc), parent=self.window)

    def copy_or_move(self):
        if not self.authorize("workspace_write"):
            return
        source = filedialog.askopenfilename(parent=self.window, title="Escolha o arquivo de origem")
        if not source:
            return
        destination = filedialog.askdirectory(parent=self.window, title="Escolha a pasta de destino")
        if not destination:
            return
        src, dst = Path(source).resolve(), Path(destination).resolve()
        if src == dst or dst in src.parents:
            messagebox.showwarning("Destino inválido", "Escolha uma pasta de destino diferente.", parent=self.window)
            return
        move = self._confirm("Tipo de operação", "Deseja MOVER o arquivo?\nEscolha Não para COPIAR.")
        verb = "mover" if move else "copiar"
        if not self._confirm("Confirmar arquivo", f"Confirmar {verb}?\n{src.name}\nPara: {dst}"):
            return
        try:
            if move:
                shutil.move(str(src), str(dst / src.name))
            else:
                shutil.copy2(str(src), str(dst / src.name))
            self.on_log(f"Arquivo {verb}: {src.name}")
        except Exception as exc:
            messagebox.showerror("Operação de arquivo", str(exc), parent=self.window)

    def install_python_package(self):
        if not self.authorize("install_dependency"):
            return
        package = simpledialog.askstring(
            "Instalar pacote Python",
            "Nome do pacote PyPI (somente nome, sem versão ou comando):",
            parent=self.window
        )
        if not package:
            return
        try:
            package = validate_package_name(package)
        except ValueError as exc:
            messagebox.showwarning("Nome inválido", str(exc), parent=self.window)
            return

        default_dir = Path.home() / "Documents" / "JarvisProjects"
        initial_dir = str(default_dir if default_dir.is_dir() else Path.home())
        project = filedialog.askdirectory(
            parent=self.window,
            title="Escolha a pasta do projeto Python que receberá o ambiente .venv",
            initialdir=initial_dir,
            mustexist=True
        )
        if not project:
            return
        project_dir = Path(project).expanduser().resolve()
        try:
            venv_dir, interpreter = validate_project_venv(project_dir)
        except ValueError as exc:
            messagebox.showerror("Ambiente inválido", str(exc), parent=self.window)
            return

        launcher = resolve_python_launcher()
        if not launcher:
            messagebox.showerror(
                "Python 3 não encontrado",
                "O JARVIS EXE não inclui um interpretador Python instalável. "
                "Instale Python 3 no Windows e habilite o launcher 'py' ou o comando 'python'. "
                "Nenhuma alteração foi feita.",
                parent=self.window
            )
            return

        if venv_dir.exists() and not interpreter.is_file():
            messagebox.showerror(
                "Ambiente .venv incompleto",
                "A pasta .venv já existe, mas não contém o interpretador esperado. "
                "O JARVIS não vai sobrescrevê-la. Revise ou renomeie essa pasta manualmente.",
                parent=self.window
            )
            return

        create_needed = not venv_dir.exists()
        action = (
            f"Projeto: {project_dir}\n"
            f"Pacote: {package}\n"
            f"Ambiente: {venv_dir}\n"
            + ("Será criado um ambiente virtual novo.\n" if create_needed else "O ambiente virtual existente será reutilizado.\n")
            + "O pip poderá baixar e executar código de terceiros durante a instalação. "
            "A instalação ficará isolada neste projeto e não será adicionada ao JARVIS.exe."
        )
        if not self._confirm("Confirmar instalação isolada", action):
            return

        try:
            installed_venv, installed_interpreter = install_package_in_project(
                project_dir, package, launcher
            )
            self.on_log(f"Pacote instalado no .venv do projeto: {package}")
            messagebox.showinfo(
                "Instalação concluída",
                f"{package} foi instalado no ambiente:\n{installed_venv}\n\n"
                "No VS Code, selecione o interpretador .venv\\Scripts\\python.exe "
                "(Windows) para usar esse pacote.",
                parent=self.window
            )
        except EnvironmentInstallError as exc:
            self.on_log(f"Falha na instalação do pacote no .venv: {package}")
            messagebox.showerror("Falha na instalação", str(exc), parent=self.window)
        except subprocess.TimeoutExpired:
            messagebox.showerror(
                "Tempo esgotado",
                "A criação do ambiente ou a instalação excedeu o limite de tempo. "
                "Verifique o estado da pasta .venv antes de tentar novamente.",
                parent=self.window
            )
        except OSError:
            messagebox.showerror(
                "Falha ao iniciar Python",
                "O Windows não conseguiu iniciar o Python/pip. Verifique a instalação do Python 3.",
                parent=self.window
            )

    def install_windows_package(self):
        if not self.authorize("install_software"):
            return
        package_id = simpledialog.askstring("Instalar aplicativo", "ID exato do pacote WinGet:", parent=self.window)
        if not package_id:
            return
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]{1,119}", package_id):
            messagebox.showwarning("ID inválido", "Informe somente o ID do pacote, sem parâmetros.", parent=self.window)
            return
        winget = shutil.which("winget.exe") or shutil.which("winget")
        if not winget:
            messagebox.showerror("WinGet indisponível", "O WinGet não foi encontrado neste Windows.", parent=self.window)
            return
        if not self._confirm(
            "Confirmar instalação",
            f"Solicitar ao WinGet a instalação do pacote '{package_id}'?\n"
            "O instalador pode exibir etapas próprias e exigir permissões do Windows."
        ):
            return
        try:
            subprocess.Popen(
                [winget, "install", "--id", package_id, "--exact",
                 "--accept-package-agreements", "--accept-source-agreements"],
                shell=False
            )
            self.on_log("Solicitada instalação WinGet: " + package_id)
        except Exception as exc:
            messagebox.showerror("WinGet", str(exc), parent=self.window)

    def _require_pyautogui(self):
        if pyautogui is None:
            messagebox.showerror(
                "Dependência ausente",
                "O controle de mouse e teclado requer pyautogui. Instale as dependências do JARVIS.",
                parent=self.window
            )
            return False
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.12
        return True

    def click(self):
        if not self.authorize("mouse_keyboard") or not self._require_pyautogui():
            return
        try:
            x, y = int(self.x_entry.get()), int(self.y_entry.get())
        except ValueError:
            messagebox.showwarning("Coordenadas", "Informe números inteiros para X e Y.", parent=self.window)
            return
        width, height = pyautogui.size()
        if not (0 <= x < width and 0 <= y < height):
            messagebox.showwarning("Coordenadas", f"A tela mede {width} × {height}.", parent=self.window)
            return
        if self._confirm("Confirmar clique", f"Clicar uma vez na posição X={x}, Y={y}?"):
            try:
                pyautogui.click(x, y)
                self.on_log(f"Clique executado em ({x}, {y}).")
            except Exception as exc:
                messagebox.showerror("Mouse", str(exc), parent=self.window)

    def type_text(self):
        if not self.authorize("mouse_keyboard") or not self._require_pyautogui():
            return
        value = simpledialog.askstring("Digitar texto", "Texto que será digitado na janela em foco:", parent=self.window)
        if value is None:
            return
        if not self._confirm("Confirmar digitação", f"Digitar o texto abaixo na janela em foco?\n\n{value[:300]}"):
            return
        try:
            pyautogui.write(value, interval=0.015)
            self.on_log("Texto digitado na janela em foco.")
        except Exception as exc:
            messagebox.showerror("Teclado", str(exc), parent=self.window)

    def hotkey(self):
        if not self.authorize("mouse_keyboard") or not self._require_pyautogui():
            return
        value = simpledialog.askstring(
            "Atalho de teclado",
            "Atalho permitido: " + ", ".join(_SAFE_HOTKEYS.keys()),
            parent=self.window
        )
        if not value:
            return
        keys = _SAFE_HOTKEYS.get(value.strip().lower())
        if not keys:
            messagebox.showwarning("Atalho não permitido", "Esse atalho não está na lista segura.", parent=self.window)
            return
        if self._confirm("Confirmar atalho", f"Enviar {value.strip()} para a janela em foco?"):
            try:
                pyautogui.hotkey(*keys)
                self.on_log("Atalho enviado: " + value.strip().lower())
            except Exception as exc:
                messagebox.showerror("Teclado", str(exc), parent=self.window)

    def refresh_processes(self):
        self.processes.delete(0, "end")
        if psutil is None:
            self.processes.insert("end", "psutil não instalado")
            return
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                self.processes.insert("end", f"{proc.info['pid']}  {proc.info['name'] or 'processo'}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def terminate_process(self):
        if not self.authorize("process_terminate"):
            return
        if psutil is None:
            messagebox.showerror("Processos", "psutil não está instalado.", parent=self.window)
            return
        selected = self.processes.curselection()
        if not selected:
            messagebox.showinfo("Processos", "Selecione um processo.", parent=self.window)
            return
        line = self.processes.get(selected[0])
        match = re.match(r"^\s*(\d+)\s+(.+)$", line)
        if not match:
            return
        pid, name = int(match.group(1)), match.group(2)
        if name.lower() in _BLOCKED_PROCESSES or pid == os.getpid():
            messagebox.showwarning("Processo protegido", "O JARVIS não encerra esse processo.", parent=self.window)
            return
        if not self._confirm(
            "Encerrar processo",
            f"Solicitar encerramento do processo?\n{ name } (PID {pid})\n"
            "Isso pode fazer você perder alterações não salvas no aplicativo."
        ):
            return
        try:
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=5)
            self.on_log(f"Processo encerrado: {name} (PID {pid}).")
            self.refresh_processes()
        except psutil.TimeoutExpired:
            messagebox.showwarning("Processo", "O processo não encerrou no tempo esperado. Nenhum encerramento forçado foi tentado.", parent=self.window)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            messagebox.showerror("Processo", str(exc), parent=self.window)
