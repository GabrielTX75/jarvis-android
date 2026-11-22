import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from memory_store import LocalMemory

class LocalMemoryTests(unittest.TestCase):
    def test_remember_persists_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LocalMemory(Path(folder) / "memory.json")
            store.remember("  Prefere   respostas curtas ")
            store.remember("prefere respostas curtas")
            self.assertEqual(store.list(), ["Prefere respostas curtas"])
            self.assertIn("Prefere respostas curtas", store.prompt_context())

    def test_forget_one_and_all(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LocalMemory(Path(folder) / "memory.json")
            store.remember("um")
            store.remember("dois")
            self.assertEqual(store.forget(1), "um")
            self.assertEqual(store.list(), ["dois"])
            self.assertEqual(store.forget(), 1)
            self.assertEqual(store.list(), [])

    def test_rejects_empty_oversized_and_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LocalMemory(Path(folder) / "memory.json", max_chars=5)
            with self.assertRaises(ValueError):
                store.remember(" ")
            with self.assertRaises(ValueError):
                store.remember("grande demais")
            with self.assertRaises(ValueError):
                store.remember("minha API key secreta")

if __name__ == "__main__":
    unittest.main()
