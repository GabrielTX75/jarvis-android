"""Desktop actions with explicit authorization and conservative defaults."""
import os, subprocess, webbrowser
from pathlib import Path
from urllib.parse import quote_plus

ALLOWED_APPS = {
    "bloco de notas": ["notepad.exe"],
    "calculadora": ["calc.exe"],
}

def open_allowed_app(name):
    key=name.strip().lower()
    if key not in ALLOWED_APPS:
        raise ValueError("Aplicativo fora da lista permitida.")
    return subprocess.Popen(ALLOWED_APPS[key], shell=False)

def open_search(query):
    if not query or len(query)>300:
        raise ValueError("Pesquisa vazia ou muito longa.")
    return webbrowser.open("https://www.google.com/search?q="+quote_plus(query))

def capture_screen(destination):
    """Capture only when explicitly invoked by the user; requires Pillow."""
    try:
        import pyautogui
    except ImportError as exc:
        raise RuntimeError("Instale pyautogui e Pillow para habilitar captura solicitada.") from exc
    path=Path(destination).expanduser().resolve()
    if path.suffix.lower() not in {".png",".jpg",".jpeg"}:
        raise ValueError("Use PNG ou JPG.")
    path.parent.mkdir(parents=True,exist_ok=True)
    pyautogui.screenshot().save(path)
    return path

def read_screen_text(image_path):
    """OCR is optional and local; requires Tesseract installed by the user."""
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("OCR opcional requer Pillow e pytesseract.") from exc
    return pytesseract.image_to_string(Image.open(image_path), lang="por+eng")
