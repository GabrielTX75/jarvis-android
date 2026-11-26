import sys
import unittest
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from voice_session import classify_confirmation, run_continuous_session


class WaitTimeoutError(Exception):
    pass


class UnknownValueError(Exception):
    pass


class RequestError(Exception):
    pass


class FakeMicrophone:
    def __enter__(self):
        return object()

    def __exit__(self, *args):
        return False


class FakeSpeechModule:
    WaitTimeoutError = WaitTimeoutError
    UnknownValueError = UnknownValueError
    RequestError = RequestError
    Microphone = FakeMicrophone

    def __init__(self, recognizer):
        self.recognizer = recognizer

    def Recognizer(self):
        return self.recognizer


class FakeRecognizer:
    def __init__(self, audio_results, transcriptions):
        self.audio_results = iter(audio_results)
        self.transcriptions = iter(transcriptions)
        self.listen_calls = []
        self.languages = []

    def adjust_for_ambient_noise(self, source, duration):
        self.calibration_duration = duration

    def listen(self, source, **kwargs):
        self.listen_calls.append(kwargs)
        result = next(self.audio_results)
        if isinstance(result, Exception):
            raise result
        return result

    def recognize_google(self, audio, language):
        self.languages.append(language)
        result = next(self.transcriptions)
        if isinstance(result, Exception):
            raise result
        return result


class VoiceSessionTests(unittest.TestCase):
    def test_timeout_then_phrase_continues(self):
        stop_event = threading.Event()
        resume_event = threading.Event()
        resume_event.set()
        recognizer = FakeRecognizer([WaitTimeoutError(), "audio"], ["Abrir agenda"])
        received = []

        def receive(text):
            received.append(text)
            stop_event.set()
            resume_event.set()

        run_continuous_session(
            FakeSpeechModule(recognizer), stop_event, resume_event, receive
        )

        self.assertEqual(received, ["Abrir agenda"])
        self.assertEqual(len(recognizer.listen_calls), 2)
        self.assertEqual(
            recognizer.listen_calls[-1],
            {"timeout": 1, "phrase_time_limit": 12},
        )
        self.assertEqual(recognizer.languages, ["pt-BR"])
        self.assertEqual(recognizer.calibration_duration, 0.8)
        self.assertEqual(recognizer.operation_timeout, 12)

    def test_session_pauses_after_phrase_until_resumed(self):
        stop_event = threading.Event()
        resume_event = threading.Event()
        resume_event.set()
        recognizer = FakeRecognizer(["audio-1", "audio-2"], ["Primeiro", "Segundo"])
        first_phrase = threading.Event()
        received = []

        def receive(text):
            received.append(text)
            if len(received) == 1:
                first_phrase.set()
            else:
                stop_event.set()
                resume_event.set()

        worker = threading.Thread(
            target=run_continuous_session,
            args=(FakeSpeechModule(recognizer), stop_event, resume_event, receive),
            daemon=True,
        )
        worker.start()
        self.assertTrue(first_phrase.wait(timeout=1))
        time.sleep(0.08)
        self.assertEqual(len(recognizer.listen_calls), 1)
        resume_event.set()
        worker.join(timeout=1)

        self.assertFalse(worker.is_alive())
        self.assertEqual(received, ["Primeiro", "Segundo"])
        self.assertEqual(len(recognizer.listen_calls), 2)

    def test_unrecognized_phrase_does_not_end_session(self):
        stop_event = threading.Event()
        resume_event = threading.Event()
        resume_event.set()
        recognizer = FakeRecognizer(
            ["audio-1", "audio-2"], [UnknownValueError(), "Olá"]
        )
        received = []
        statuses = []

        def receive(text):
            received.append(text)
            stop_event.set()
            resume_event.set()

        run_continuous_session(
            FakeSpeechModule(recognizer),
            stop_event,
            resume_event,
            receive,
            on_status=statuses.append,
        )

        self.assertEqual(received, ["Olá"])
        self.assertTrue(any("NÃO ENTENDI" in item for item in statuses))

    def test_network_error_is_reported(self):
        stop_event = threading.Event()
        resume_event = threading.Event()
        resume_event.set()
        recognizer = FakeRecognizer(["audio"], [RequestError()])
        errors = []

        run_continuous_session(
            FakeSpeechModule(recognizer),
            stop_event,
            resume_event,
            lambda _text: self.fail("No phrase should be delivered"),
            on_error=errors.append,
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("INTERNET", errors[0])

    def test_explicit_confirmation_phrases(self):
        self.assertEqual(classify_confirmation("Confirmar!"), "confirm")
        self.assertEqual(classify_confirmation("pode confirmar"), "confirm")
        self.assertEqual(classify_confirmation("CANCELAR"), "cancel")
        self.assertEqual(classify_confirmation("não"), "cancel")
        self.assertIsNone(classify_confirmation("talvez"))


if __name__ == "__main__":
    unittest.main()
