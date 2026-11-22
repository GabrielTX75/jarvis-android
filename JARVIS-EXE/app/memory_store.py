"""Explicit, local-only memory for JARVIS EXE.

Only facts the user explicitly asks to remember are stored. No cloud sync.
The store is bounded and written atomically to avoid corrupting the file.
"""
import json
import os
from pathlib import Path

class LocalMemory:
    def __init__(self, path, max_items=100, max_chars=500):
        self.path = Path(path)
        self.max_items = max_items
        self.max_chars = max_chars

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, ValueError, TypeError):
            return []

    def list(self):
        return [str(x) for x in self._load() if isinstance(x, str)]

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
        if value.casefold() not in {x.casefold() for x in items}:
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
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, self.path)

    def prompt_context(self, limit=20):
        items = self.list()[-limit:]
        if not items:
            return ""
        return "FATOS SALVOS LOCALMENTE A PEDIDO DO USUÁRIO (podem estar desatualizados):\n" + "\n".join(f"- {x}" for x in items)
