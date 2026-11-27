"""Explicit, local-only memory for JARVIS EXE.

Memory is encrypted at rest with Windows DPAPI for the current Windows user.
Legacy plaintext JSON is migrated on first read. No plaintext fallback is used.
"""
import ctypes
import json
import os
from pathlib import Path


_FILE_HEADER = b"JARVIS-MEMORY-DPAPI-V1\n"
_UI_FORBIDDEN = 0x1


class MemoryStorageError(RuntimeError):
    """Raised when encrypted local memory cannot be read or written safely."""


def _dpapi_transform(data, decrypt=False):
    """Protect/unprotect bytes using DPAPI, scoped to the current Windows user."""
    if os.name != "nt":
        raise MemoryStorageError(
            "A memória protegida exige o Windows. Nenhum dado foi salvo em texto puro."
        )

    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    output = DATA_BLOB()
    local_free = None
    description = wintypes.LPWSTR()
    try:
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        source_buffer = ctypes.create_string_buffer(data, len(data))
        source = DATA_BLOB(
            len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte))
        )
        local_free = kernel32.LocalFree
        local_free.argtypes = [ctypes.c_void_p]
        local_free.restype = ctypes.c_void_p

        if decrypt:
            transform = crypt32.CryptUnprotectData
            transform.argtypes = [
                ctypes.POINTER(DATA_BLOB),
                ctypes.POINTER(wintypes.LPWSTR),
                ctypes.POINTER(DATA_BLOB),
                ctypes.c_void_p,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.POINTER(DATA_BLOB),
            ]
            transform.restype = wintypes.BOOL
            succeeded = transform(
                ctypes.byref(source),
                ctypes.byref(description),
                None,
                None,
                None,
                _UI_FORBIDDEN,
                ctypes.byref(output),
            )
        else:
            transform = crypt32.CryptProtectData
            transform.argtypes = [
                ctypes.POINTER(DATA_BLOB),
                wintypes.LPCWSTR,
                ctypes.POINTER(DATA_BLOB),
                ctypes.c_void_p,
                ctypes.c_void_p,
                wintypes.DWORD,
                ctypes.POINTER(DATA_BLOB),
            ]
            transform.restype = wintypes.BOOL
            succeeded = transform(
                ctypes.byref(source),
                "JARVIS local memory",
                None,
                None,
                None,
                _UI_FORBIDDEN,
                ctypes.byref(output),
            )

        if not succeeded:
            raise ctypes.WinError(ctypes.get_last_error())
        return ctypes.string_at(output.pbData, output.cbData)
    except Exception as exc:
        if isinstance(exc, MemoryStorageError):
            raise
        action = "descriptografar" if decrypt else "proteger"
        raise MemoryStorageError(
            f"O Windows não conseguiu {action} a memória local. O arquivo original foi preservado."
        ) from exc
    finally:
        # DPAPI allocates its output and optional description with LocalAlloc.
        if local_free is not None:
            try:
                if output.pbData:
                    local_free(ctypes.cast(output.pbData, ctypes.c_void_p))
            except Exception:
                pass
            try:
                if description:
                    local_free(ctypes.cast(description, ctypes.c_void_p))
            except Exception:
                pass


class LocalMemory:
    def __init__(self, path, max_items=100, max_chars=500,
                 protector=None, unprotector=None):
        self.path = Path(path)
        self.max_items = max_items
        self.max_chars = max_chars
        self._protector = protector or (lambda value: _dpapi_transform(value, decrypt=False))
        self._unprotector = unprotector or (lambda value: _dpapi_transform(value, decrypt=True))

    def _load(self):
        if not self.path.exists():
            return []
        try:
            raw = self.path.read_bytes()
        except OSError as exc:
            raise MemoryStorageError("Não foi possível ler o arquivo de memória local.") from exc

        if raw.startswith(_FILE_HEADER):
            try:
                payload = self._unprotector(raw[len(_FILE_HEADER):])
                data = json.loads(payload.decode("utf-8"))
            except Exception as exc:
                raise MemoryStorageError(
                    "A memória criptografada não pôde ser aberta. O arquivo foi preservado; "
                    "verifique se você está na mesma conta do Windows."
                ) from exc
        else:
            # One-time migration from the previous plaintext JSON format.
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                raise MemoryStorageError(
                    "O arquivo antigo de memória está inválido. Ele foi preservado sem alterações."
                ) from exc
            if not isinstance(data, list) or any(not isinstance(item, str) for item in data):
                raise MemoryStorageError(
                    "O formato antigo de memória é inválido. O arquivo foi preservado."
                )
            self._save(data[-self.max_items:])

        if not isinstance(data, list) or any(not isinstance(item, str) for item in data):
            raise MemoryStorageError(
                "O conteúdo da memória local é inválido. O arquivo foi preservado."
            )
        return data[-self.max_items:]

    def list(self):
        return self._load()

    def remember(self, fact):
        value = " ".join(str(fact).split()).strip()
        if not value:
            raise ValueError("Informe algo para lembrar.")
        if len(value) > self.max_chars:
            raise ValueError(f"A memória aceita até {self.max_chars} caracteres por item.")
        import re
        if re.search(r"(?i)\b(api[_ -]?key|senha|password|token|secret|chave privada|private key)\b", value):
            raise ValueError("Não salve senhas, tokens ou chaves de API na memória do JARVIS.")
        items = self.list()
        if value.casefold() not in {item.casefold() for item in items}:
            items.append(value)
        self._save(items[-self.max_items:])
        return value

    def forget(self, index=None):
        items = self.list()
        if index is None:
            self._save([])
            return len(items)
        if index < 1 or index > len(items):
            raise IndexError("Número de memória inválido.")
        removed = items.pop(index - 1)
        self._save(items)
        return removed

    def _save(self, items):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8")
        try:
            encrypted = _FILE_HEADER + self._protector(payload)
        except Exception as exc:
            if isinstance(exc, MemoryStorageError):
                raise
            raise MemoryStorageError(
                "Não foi possível criptografar a memória. Nenhum dado foi salvo em texto puro."
            ) from exc

        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temp.open("wb") as stream:
                stream.write(encrypted)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise MemoryStorageError("Não foi possível salvar a memória criptografada.") from exc

    def prompt_context(self, limit=20):
        items = self.list()[-limit:]
        if not items:
            return ""
        return "FATOS SALVOS LOCALMENTE A PEDIDO DO USUÁRIO (podem estar desatualizados):\n" + "\n".join(f"- {item}" for item in items)
