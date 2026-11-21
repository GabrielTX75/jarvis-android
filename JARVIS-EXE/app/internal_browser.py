"""JARVIS-owned browser window using Microsoft Edge WebView2 on Windows."""
import threading
import tkinter as tk
from tkinter import messagebox
from urllib.parse import quote_plus, urlparse

try:
    import webview
except Exception:
    webview = None


class InternalBrowser:
    def __init__(self, root, initial_url="https://www.google.com"):
        self.root = root
        self.window = None
        self.thread = None
        self.initial_url = self._safe_url(initial_url)
        if webview is None:
            messagebox.showerror(
                "Navegador JARVIS",
                "O componente WebView2 não está instalado neste pacote. "
                "Instale o Microsoft Edge WebView2 Runtime e a dependência pywebview."
            )
            return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    @staticmethod
    def _safe_url(value):
        value = (value or "").strip()
        if not value:
            return "https://www.google.com"
        if " " in value and "." not in value:
            return "https://www.google.com/search?q=" + quote_plus(value)
        if "://" not in value:
            value = "https://" + value
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Use um endereço HTTP ou HTTPS válido.")
        return value

    def _run(self):
        try:
            self.window = webview.create_window(
                "JARVIS • Navegador interno",
                self.initial_url,
                width=1180,
                height=820,
                min_size=(760, 520),
                text_select=True,
                confirm_close=True
            )
            webview.start(gui="edgechromium", debug=False, private_mode=False)
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror(
                "Navegador JARVIS",
                "Não foi possível iniciar o navegador interno: " + str(exc)
            ))

    def navigate(self, url):
        try:
            target = self._safe_url(url)
        except ValueError as exc:
            messagebox.showerror("Endereço inválido", str(exc))
            return
        if self.window is None:
            messagebox.showinfo("Navegador JARVIS", "A janela do navegador ainda está iniciando.")
            return
        try:
            self.window.load_url(target)
        except Exception as exc:
            messagebox.showerror("Navegador JARVIS", str(exc))
