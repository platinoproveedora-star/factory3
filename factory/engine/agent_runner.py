"""Generic agent runner."""

from __future__ import annotations

from typing import Any

from .agent_loader import AgentLoader


class AgentRunner:
    """Executes an agent through the generic run(context) contract."""

    def __init__(self, loader: AgentLoader):
        self.loader = loader

    def run(self, name: str, context: dict[str, Any]) -> dict[str, Any]:
        spec = self.loader.inspect(name)
        module = self.loader.load_module(spec)

        run = getattr(module, "run", None)
        if not callable(run):
            return {
                "ok": False,
                "error": f"Agent '{name}' does not expose run(context)",
            }

        result = run(context)
        if not isinstance(result, dict):
            return {
                "ok": False,
                "error": f"Agent '{name}' returned a non-dict result",
            }

        return result

