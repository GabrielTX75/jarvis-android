"""JARVIS no terminal. Digite o pedido; com voz configurada, também pode falar e ouvir.

Voz é opcional e não é testada automaticamente:
- Saída: instale pyttsx3.
- Entrada: instale vosk e sounddevice e defina JARVIS_VOSK_MODELO com a pasta do modelo pt-BR.
"""
from __future__ import annotations

import os
import sys

from . import config
from .nucleo import Nucleo


def _falar_fn():
    try:
        import pyttsx3  # type: ignore[import-not-found]
    except ImportError:
        return None
    motor = pyttsx3.init()

    def falar(texto: str) -> None:
        motor.say(texto)
        motor.runAndWait()

    return falar


def _ouvir_fn():
    modelo = os.environ.get("JARVIS_VOSK_MODELO", "").strip()
    if not modelo:
        return None
    try:
        import json
        import queue

        import sounddevice as sd  # type: ignore[import-not-found]
        from vosk import KaldiRecognizer, Model  # type: ignore[import-not-found]
    except ImportError:
        return None
    reconhecedor_modelo = Model(modelo)
    fila: queue.Queue[bytes] = queue.Queue()

    def callback(indata, frames, tempo, status):
        fila.put(bytes(indata))

    def ouvir() -> str:
        rec = KaldiRecognizer(reconhecedor_modelo, 16000)
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1, callback=callback):
            print("Ouvindo... fale e faça uma pausa para eu entender.")
            while True:
                if rec.AcceptWaveform(fila.get()):
                    texto = json.loads(rec.Result()).get("text", "")
                    if texto:
                        return texto

    return ouvir


def _aviso(mensagem: str) -> None:
    print(f"\nJARVIS: {mensagem}\n> ", end="", flush=True)


def main(argv: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argv is None else argv
    if "--configurar" in argumentos:
        from .configurar import configurar

        print(configurar())
        return 0
    nucleo = Nucleo(aviso=_aviso)
    if not config.valor("ia_url"):
        print("Dica: para usar a IA, rode 'JARVIS-PC --configurar' (ou 'python -m jarvis --configurar').")
    falar = _falar_fn()
    ouvir = _ouvir_fn()
    print("JARVIS para computador. Digite seu pedido, ou 'sair' para fechar.")
    while True:
        try:
            if ouvir:
                digitado = input("(Enter para falar, ou digite) > ").strip()
                texto = digitado or ouvir()
            else:
                texto = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not texto:
            continue
        resposta, encerrar = nucleo.processar(texto)
        print(f"JARVIS: {resposta}")
        if falar:
            falar(resposta)
        if encerrar:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
