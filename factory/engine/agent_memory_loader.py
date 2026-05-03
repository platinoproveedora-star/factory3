"""Loader for portable agent memories."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from .agent_loader import AgentLoader


class AgentMemoryLoader:
    """Loads and executes agent memory modules."""

    def __init__(self, agents_root: Path):
        self.agents_root = Path(agents_root)
        self.agent_loader = AgentLoader(self.agents_root)

    def has_memory(self, agent_name: str) -> bool:
        try:
            spec = self.agent_loader.inspect(agent_name)
        except Exception:
            return False
        memory = spec.metadata.get("memory", {})
        return isinstance(memory, dict) and bool(memory) and bool(memory.get("entrypoint", "agent_memory.py"))

    def search(self, agent_name: str, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        module_result = self._load_memory_module(agent_name)
        if not module_result.get("ok"):
            return module_result
        search = getattr(module_result["module"], "search", None)
        if not callable(search):
            return {"ok": False, "error": f"agent memory no expone search(query, context): {agent_name}"}
        result = search(query, context or {})
        return result if isinstance(result, dict) else {"ok": False, "error": "agent memory search retorno no-dict"}

    def remember(
        self,
        agent_name: str,
        user_message: str,
        assistant_response: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        module_result = self._load_memory_module(agent_name)
        if not module_result.get("ok"):
            return module_result
        remember = getattr(module_result["module"], "remember", None)
        if not callable(remember):
            return {"ok": False, "error": f"agent memory no expone remember(...): {agent_name}"}
        result = remember(user_message, assistant_response, context or {})
        return result if isinstance(result, dict) else {"ok": False, "error": "agent memory remember retorno no-dict"}

    def _load_memory_module(self, agent_name: str) -> dict[str, Any]:
        spec = self.agent_loader.inspect(agent_name)
        memory = spec.metadata.get("memory", {})
        if not isinstance(memory, dict):
            return {"ok": False, "error": f"agente sin memoria configurada: {agent_name}"}

        entrypoint = spec.path / memory.get("entrypoint", "agent_memory.py")
        if not entrypoint.exists():
            return {"ok": False, "error": f"agent memory no existe: {entrypoint}"}

        return {"ok": True, "module": self._load_module(agent_name, spec.path, entrypoint)}

    def _load_module(self, agent_name: str, agent_path: Path, entrypoint: Path) -> ModuleType:
        module_name = f"factory_agent_memory_{agent_name.replace('-', '_')}"
        module_spec = importlib.util.spec_from_file_location(module_name, entrypoint)
        if not module_spec or not module_spec.loader:
            raise ImportError(f"Cannot import agent memory entrypoint: {entrypoint}")

        module = importlib.util.module_from_spec(module_spec)
        path_text = str(agent_path)
        sys.path.insert(0, path_text)
        try:
            module_spec.loader.exec_module(module)
        finally:
            if sys.path and sys.path[0] == path_text:
                sys.path.pop(0)
        return module
