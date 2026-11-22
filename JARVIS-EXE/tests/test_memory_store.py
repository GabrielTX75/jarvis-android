import tempfile
import unittest
from pathlib import Path

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

    def test_rejects_empty_and_oversized(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LocalMemory(Path(folder) / "memory.json", max_chars=5)
            with self.assertRaises(ValueError):
                store.remember(" ")
            with self.assertRaises(ValueError):
                store.remember("grande demais")

if __name__ == "__main__":
    unittest.main()
