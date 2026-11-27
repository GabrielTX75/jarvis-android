import json
import os
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from memory_store import LocalMemory, MemoryStorageError, _FILE_HEADER


def test_protect(value):
    return b"TEST-ENCRYPTED:" + value[::-1]


def test_unprotect(value):
    prefix = b"TEST-ENCRYPTED:"
    if not value.startswith(prefix):
        raise ValueError("invalid test ciphertext")
    return value[len(prefix):][::-1]


def make_store(path, **kwargs):
    return LocalMemory(path, protector=test_protect, unprotector=test_unprotect, **kwargs)


class LocalMemoryTests(unittest.TestCase):
    def test_remember_persists_encrypted_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.json"
            store = make_store(path)
            store.remember("  Prefere   respostas curtas ")
            store.remember("prefere respostas curtas")
            self.assertEqual(store.list(), ["Prefere respostas curtas"])
            self.assertIn("Prefere respostas curtas", store.prompt_context())
            stored = path.read_bytes()
            self.assertTrue(stored.startswith(_FILE_HEADER))
            self.assertNotIn(b"Prefere respostas curtas", stored)

    def test_forget_one_and_all(self):
        with tempfile.TemporaryDirectory() as folder:
            store = make_store(Path(folder) / "memory.json")
            store.remember("um")
            store.remember("dois")
            self.assertEqual(store.forget(1), "um")
            self.assertEqual(store.list(), ["dois"])
            self.assertEqual(store.forget(), 1)
            self.assertEqual(store.list(), [])

    def test_rejects_empty_oversized_and_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            store = make_store(Path(folder) / "memory.json", max_chars=5)
            with self.assertRaises(ValueError):
                store.remember(" ")
            with self.assertRaises(ValueError):
                store.remember("grande demais")
            with self.assertRaises(ValueError):
                store.remember("minha API key secreta")

    def test_migrates_legacy_plaintext_on_first_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.json"
            path.write_text(json.dumps(["fato legado"], ensure_ascii=False), encoding="utf-8")
            store = make_store(path)
            self.assertEqual(store.list(), ["fato legado"])
            migrated = path.read_bytes()
            self.assertTrue(migrated.startswith(_FILE_HEADER))
            self.assertNotIn("fato legado".encode("utf-8"), migrated)

    def test_migration_keeps_only_the_configured_number_of_items(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.json"
            path.write_text(json.dumps(["um", "dois", "três"]), encoding="utf-8")
            store = make_store(path, max_items=2)
            self.assertEqual(store.list(), ["dois", "três"])
            payload = test_unprotect(path.read_bytes()[len(_FILE_HEADER):])
            self.assertEqual(json.loads(payload.decode("utf-8")), ["dois", "três"])

    def test_protection_failure_never_creates_plaintext_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.json"
            def fail_protect(value):
                raise RuntimeError("proteção indisponível")
            store = LocalMemory(path, protector=fail_protect, unprotector=test_unprotect)
            with self.assertRaises(MemoryStorageError):
                store.remember("não gravar em texto puro")
            self.assertFalse(path.exists())

    def test_corrupt_encrypted_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.json"
            original = _FILE_HEADER + b"not-a-valid-ciphertext"
            path.write_bytes(original)
            store = make_store(path)
            with self.assertRaises(MemoryStorageError):
                store.list()
            self.assertEqual(path.read_bytes(), original)

    def test_invalid_legacy_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.json"
            original = b"{broken json"
            path.write_bytes(original)
            store = make_store(path)
            with self.assertRaises(MemoryStorageError):
                store.list()
            self.assertEqual(path.read_bytes(), original)

    @unittest.skipUnless(os.name == "nt", "DPAPI real test runs only on Windows")
    def test_default_dpapi_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.json"
            store = LocalMemory(path)
            store.remember("protegido pelo Windows")
            self.assertNotIn("protegido pelo Windows".encode("utf-8"), path.read_bytes())
            self.assertEqual(LocalMemory(path).list(), ["protegido pelo Windows"])

    @unittest.skipIf(os.name == "nt", "non-Windows fail-closed check")
    def test_default_backend_fails_closed_off_windows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.json"
            store = LocalMemory(path)
            with self.assertRaises(MemoryStorageError):
                store.remember("não gravar em texto puro")
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
