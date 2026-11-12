"""Ponto de entrada do executável (usado pelo PyInstaller)."""
import sys

from jarvis.main import main

if __name__ == "__main__":
    sys.exit(main())
