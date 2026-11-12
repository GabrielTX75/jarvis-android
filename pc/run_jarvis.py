"""Ponto de entrada do programa e do executável (PyInstaller).

Sem argumentos: abre a janela.
--terminal: modo de texto.   --teste: só confirma que o programa inicia (usado no build).
"""
import sys

if __name__ == "__main__":
    if "--teste" in sys.argv:
        from jarvis import __version__

        print("JARVIS " + __version__)
        sys.exit(0)
    if "--terminal" in sys.argv:
        from jarvis.main import main

        sys.exit(main())
    from jarvis.interface import iniciar

    iniciar()
