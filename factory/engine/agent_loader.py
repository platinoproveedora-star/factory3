"""Generic agent discovery and import helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any


@dataclass(frozen=True)
class AgentSpec:
    name: str
    path: Path
    skill_md: Path | None
    entrypoint: Path | None
    metadata: dict[str, Any]
    kind: str = "executable"
    source_format: str = "legacy"


class AgentLoader:
    """Loads portable agents from an agents root."""

    def __init__(self, agents_root: Path):
        self.agents_root = Path(agents_root)

    def resolve_path(self, name: str) -> Path:
        return self.agents_root / name

    def inspect(self, name: str) -> AgentSpec:
        agent_path = self.resolve_path(name)
        skill_md = agent_path / "SKILL.md"
        manifest = agent_path / "manifest.json"

        if not agent_path.exists():
            raise FileNotFoundError(f"Agent not found: {agent_path}")

        metadata: dict[str, Any] = {}
        source_format = "legacy"
        if manifest.exists():
            metadata = self._read_json(manifest)
            source_format = "manifest"
        elif skill_md.exists():
            metadata = self._read_skill_md_frontmatter(skill_md)
            source_format = "skill_md"
        else:
            raise FileNotFoundError(f"Missing manifest.json or SKILL.md: {agent_path}")

        entrypoint_name = metadata.get("entrypoint", "agent.py")
        entrypoint = agent_path / entrypoint_name
        kind = metadata.get("kind")
        if not kind:
            kind = "executable" if entrypoint.exists() else "instruction_only"

        if kind == "executable" and not entrypoint.exists():
            raise FileNotFoundError(f"Missing agent entrypoint: {entrypoint}")

        return AgentSpec(
            name=metadata.get("name", name),
            path=agent_path,
            skill_md=skill_md if skill_md.exists() else None,
            entrypoint=entrypoint if entrypoint.exists() else None,
            metadata=metadata,
            kind=kind,
            source_format=source_format,
        )

    def load_module(self, spec: AgentSpec) -> ModuleType:
        if not spec.entrypoint:
            raise ImportError(f"Agent is not executable: {spec.name}")

        module_name = f"factory_agent_{spec.name.replace('-', '_')}"
        module_spec = importlib.util.spec_from_file_location(
            module_name,
            spec.entrypoint,
        )

        if not module_spec or not module_spec.loader:
            raise ImportError(f"Cannot import agent entrypoint: {spec.entrypoint}")

        module = importlib.util.module_from_spec(module_spec)
        agent_path = str(spec.path)

        local_modules = self._local_module_names(spec.path)
        previous_modules = {name: sys.modules.get(name) for name in local_modules}
        self._purge_path_modules(spec.path)
        for name in local_modules:
            sys.modules.pop(name, None)
        sys.path.insert(0, agent_path)
        try:
            module_spec.loader.exec_module(module)
        finally:
            if sys.path and sys.path[0] == agent_path:
                sys.path.pop(0)
            self._purge_path_modules(spec.path)
            for name, previous_module in previous_modules.items():
                if previous_module is not None:
                    sys.modules[name] = previous_module

        return module

    def _local_module_names(self, path: Path) -> set[str]:
        names = {child.stem for child in path.glob("*.py")}
        names.update(child.name for child in path.iterdir() if child.is_dir() and (child / "__init__.py").exists())
        return names

    def _purge_path_modules(self, path: Path) -> None:
        root = path.resolve()
        for name, module in list(sys.modules.items()):
            module_file = getattr(module, "__file__", None)
            if module_file and self._is_relative_to(Path(module_file).resolve(), root):
                sys.modules.pop(name, None)

    def _is_relative_to(self, path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
        except ValueError:
            return False
        return True

    def _read_json(self, path: Path) -> dict[str, Any]:
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw:
            return {}

        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _read_skill_md_frontmatter(self, path: Path) -> dict[str, Any]:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}

        metadata: dict[str, Any] = {}
        for line in lines[1:]:
            raw = line.strip()
            if raw == "---":
                break
            if not raw or ":" not in raw:
                continue
            key, value = raw.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"').strip("'")

        return metadata
