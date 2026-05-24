"""Generic skill discovery and import helpers.

Skills are portable folders. The loader only checks for the standard files
and imports the declared Python entrypoint when requested.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any


@dataclass(frozen=True)
class SkillSpec:
    name: str
    path: Path
    skill_md: Path | None
    entrypoint: Path | None
    metadata: dict[str, Any]
    kind: str = "executable"
    source_format: str = "legacy"


class SkillLoader:
    """Loads portable skills from internal and external skill roots."""

    def __init__(
        self,
        internal_root: Path,
        external_root: Path | None = None,
        extra_roots: dict[str, Path] | None = None,
    ):
        self.internal_root = Path(internal_root)
        self.external_root = Path(external_root) if external_root else None
        self._extra_roots: dict[str, Path] = (
            {k: Path(v) for k, v in extra_roots.items()} if extra_roots else {}
        )

    def resolve_path(self, name: str, source: str = "internos") -> Path:
        if source in ("interno", "internos", "internal"):
            direct = self.internal_root / name
            if direct.exists():
                return direct
            # Fall back to registry.json for skills in vertical subfolders
            registry = self.internal_root.parent / "registry.json"
            if registry.exists():
                try:
                    data = json.loads(registry.read_text(encoding="utf-8"))
                    rel = (data.get(name) or {}).get("path", "")
                    prefix = "skills/internos/"
                    if rel.startswith(prefix):
                        candidate = self.internal_root / rel[len(prefix):]
                        if candidate.exists():
                            return candidate
                except Exception:
                    pass
            return direct

        if source in self._extra_roots:
            return self._extra_roots[source] / name

        if source in ("externo", "externos", "external"):
            if not self.external_root:
                raise ValueError("External skill root is not configured")
            direct_path = self.external_root / name
            if direct_path.exists():
                return direct_path

            for external_kind in ("instrucciones", "ejecutables"):
                candidate = self.external_root / external_kind / name
                if candidate.exists():
                    return candidate

            return direct_path

        return Path(source) / name

    def inspect(self, name: str, source: str = "internos") -> SkillSpec:
        skill_path = self.resolve_path(name, source)
        skill_md = skill_path / "SKILL.md"
        manifest = skill_path / "manifest.json"

        if not skill_path.exists():
            raise FileNotFoundError(f"Skill not found: {skill_path}")

        metadata: dict[str, Any] = {}
        source_format = "legacy"
        if manifest.exists():
            metadata = self._read_json(manifest)
            source_format = "manifest"
        elif skill_md.exists():
            metadata = self._read_skill_md_frontmatter(skill_md)
            source_format = "skill_md"
        else:
            raise FileNotFoundError(f"Missing manifest.json or SKILL.md: {skill_path}")

        entrypoint_name = metadata.get("entrypoint", "skill.py")
        entrypoint = skill_path / entrypoint_name
        kind = metadata.get("kind")
        if not kind:
            kind = "executable" if entrypoint.exists() else "instruction_only"

        if kind == "executable" and not entrypoint.exists():
            raise FileNotFoundError(f"Missing skill entrypoint: {entrypoint}")

        return SkillSpec(
            name=metadata.get("name", name),
            path=skill_path,
            skill_md=skill_md if skill_md.exists() else None,
            entrypoint=entrypoint if entrypoint.exists() else None,
            metadata=metadata,
            kind=kind,
            source_format=source_format,
        )

    def load_module(self, spec: SkillSpec) -> ModuleType:
        if not spec.entrypoint:
            raise ImportError(f"Skill is not executable: {spec.name}")

        module_name = f"factory_skill_{spec.name.replace('-', '_')}"
        module_spec = importlib.util.spec_from_file_location(
            module_name,
            spec.entrypoint,
        )

        if not module_spec or not module_spec.loader:
            raise ImportError(f"Cannot import skill entrypoint: {spec.entrypoint}")

        module = importlib.util.module_from_spec(module_spec)
        skill_path = str(spec.path)

        local_modules = self._local_module_names(spec.path)
        previous_modules = {name: sys.modules.get(name) for name in local_modules}
        self._purge_path_modules(spec.path)
        for name in local_modules:
            sys.modules.pop(name, None)
        sys.path.insert(0, skill_path)
        try:
            module_spec.loader.exec_module(module)
        finally:
            if sys.path and sys.path[0] == skill_path:
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
