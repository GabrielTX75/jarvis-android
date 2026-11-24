"""Manual, opt-in continuous speech recognition for JARVIS EXE."""

def run_continuous_session(
    speech_module,
    stop_event,
    resume_event,
    on_text,
    on_status=None,
    on_error=None,
    language="pt-BR",
    listen_timeout=1,
    phrase_time_limit=12,
    operation_timeout=12,
):
    """Listen in short windows and pause after each utterance until the caller resumes."""
    recognizer = speech_module.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.75
    recognizer.non_speaking_duration = 0.45
    recognizer.operation_timeout = operation_timeout

    with speech_module.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.8)
        if on_status:
            on_status("MICROFONE ATIVO • FALE AGORA")

        while not stop_event.is_set():
            if not resume_event.wait(timeout=0.2):
                continue
            try:
                audio = recognizer.listen(
                    source,
                    timeout=listen_timeout,
                    phrase_time_limit=phrase_time_limit,
                )
            except speech_module.WaitTimeoutError:
                continue

            try:
                phrase = recognizer.recognize_google(audio, language=language).strip()
            except speech_module.UnknownValueError:
                if on_status:
                    on_status("NÃO ENTENDI • TENTE NOVAMENTE")
                continue
            except speech_module.RequestError:
                if on_error:
                    on_error("RECONHECIMENTO INDISPONÍVEL • VERIFIQUE A INTERNET")
                break

            if phrase and not stop_event.is_set():
                resume_event.clear()
                on_text(phrase)
                while not stop_event.is_set() and not resume_event.wait(timeout=0.2):
                    pass
