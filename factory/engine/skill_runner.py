"""Generic skill runner.

The runner only enforces the public contract: a skill entrypoint must expose
run(context: dict) -> dict.
"""

from __future__ import annotations

from typing import Any

from .skill_loader import SkillLoader


class SkillRunner:
    """Executes a skill through the generic run(context) contract."""

    def __init__(self, loader: SkillLoader):
        self.loader = loader

    def run(
        self,
        name: str,
        context: dict[str, Any],
        source: str = "internos",
    ) -> dict[str, Any]:
        spec = self.loader.inspect(name, source)
        if spec.kind not in ("executable", "data"):
            return {
                "ok": False,
                "error": f"Skill '{name}' is instruction-only and cannot be executed",
                "metadata": spec.metadata,
            }

        module = self.loader.load_module(spec)

        run = getattr(module, "run", None)
        if not callable(run):
            return {
                "ok": False,
                "error": f"Skill '{name}' does not expose run(context)",
            }

        result = run(context)
        if not isinstance(result, dict):
            return {
                "ok": False,
                "error": f"Skill '{name}' returned a non-dict result",
            }

        return result
