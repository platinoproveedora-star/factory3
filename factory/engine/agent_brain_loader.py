"""Loader for portable agent brains."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from .agent_loader import AgentLoader
from .agent_memory_loader import AgentMemoryLoader


class AgentBrainLoader:
    """Loads and executes an agent brain through respond(message, context)."""

    def __init__(self, agents_root: Path):
        self.agents_root = Path(agents_root)
        self.agent_loader = AgentLoader(self.agents_root)
        self.memory_loader = AgentMemoryLoader(self.agents_root)

    def respond(self, agent_name: str, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        spec = self.agent_loader.inspect(agent_name)
        brain = spec.metadata.get("brain", {})
        if not isinstance(brain, dict):
            return {"ok": False, "error": f"agente sin brain configurado: {agent_name}"}

        entrypoint_name = brain.get("entrypoint", "agent_brain.py")
        entrypoint = spec.path / entrypoint_name
        if not entrypoint.exists():
            return {"ok": False, "error": f"agent brain no existe: {entrypoint}"}

        module = self._load_module(agent_name, spec.path, entrypoint)
        respond = getattr(module, "respond", None)
        if not callable(respond):
            return {"ok": False, "error": f"agent brain no expone respond(message, context): {agent_name}"}

        runtime_context = dict(context or {})
        memory_result = None
        if self.memory_loader.has_memory(agent_name):
            memory_result = self.memory_loader.search(agent_name, message, runtime_context)
            if memory_result.get("ok"):
                data = memory_result.get("data", {})
                if isinstance(data, dict):
                    runtime_context["memories"] = data.get("memories", [])

        result = respond(message, runtime_context)
        if not isinstance(result, dict):
            return {"ok": False, "error": f"agent brain retorno no-dict: {agent_name}"}
        if result.get("ok") and self.memory_loader.has_memory(agent_name):
            remember_result = self.memory_loader.remember(
                agent_name,
                message,
                str(result.get("response", "")),
                runtime_context,
            )
            result.setdefault("memory", {})
            result["memory"]["search"] = memory_result
            result["memory"]["remember"] = remember_result
        return result

    def _load_module(self, agent_name: str, agent_path: Path, entrypoint: Path) -> ModuleType:
        module_name = f"factory_agent_brain_{agent_name.replace('-', '_')}"
        module_spec = importlib.util.spec_from_file_location(module_name, entrypoint)
        if not module_spec or not module_spec.loader:
            raise ImportError(f"Cannot import agent brain entrypoint: {entrypoint}")

        module = importlib.util.module_from_spec(module_spec)
        path_text = str(agent_path)
        sys.path.insert(0, path_text)
        try:
            module_spec.loader.exec_module(module)
        finally:
            if sys.path and sys.path[0] == path_text:
                sys.path.pop(0)

        return module
