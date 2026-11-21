"""JARVIS Core: deterministic command routing and capability registry.

The core is intentionally provider-neutral. It does not execute arbitrary model
output; platform modules register explicit, user-authorized handlers.
"""
from dataclasses import dataclass
from typing import Callable, Iterable, Optional


@dataclass(frozen=True)
class ModuleStatus:
    module_id: str
    name: str
    capabilities: tuple[str, ...]
    available: bool
    detail: str = ""


class ModuleRegistry:
    """Tracks real module availability; unavailable modules stay explicit."""

    def __init__(self):
        self._modules = {}

    def register(self, status: ModuleStatus):
        key = status.module_id.strip().lower()
        if not key or key in self._modules:
            raise ValueError("ID de módulo vazio ou duplicado.")
        self._modules[key] = status
        return status

    def get(self, module_id: str) -> Optional[ModuleStatus]:
        return self._modules.get(str(module_id).strip().lower())

    def list(self):
        return tuple(self._modules.values())

    def providers_for(self, capability: str):
        wanted = str(capability).strip().lower()
        return tuple(
            module for module in self._modules.values()
            if module.available and wanted in {c.lower() for c in module.capabilities}
        )


class CommandRouter:
    """Routes only to registered handlers, in explicit priority order."""

    def __init__(self):
        self._handlers = []

    def register(self, name: str, handler: Callable[[str], bool], priority=100):
        key = str(name).strip().lower()
        if not key or not callable(handler):
            raise ValueError("Handler inválido.")
        if any(item[1] == key for item in self._handlers):
            raise ValueError("Handler já registrado.")
        self._handlers.append((int(priority), key, handler))
        self._handlers.sort(key=lambda item: (item[0], item[1]))

    def dispatch(self, prompt: str) -> bool:
        text = str(prompt or "").strip()
        if not text:
            return False
        for _priority, _name, handler in self._handlers:
            if handler(text) is True:
                return True
        return False
