"""Service for context_loader — reads registries and docs to boot a new chat session."""

from __future__ import annotations

import json
from pathlib import Path


class ContextLoaderService:

    def ejecutar(self, context: dict) -> dict:
        base_dir = Path(context.get("base_dir", "factory"))
        root_dir = base_dir.parent if base_dir.is_absolute() else Path(".")

        result: dict = {}

        if context.get("include_docs", True):
            result["docs"] = self._leer_markdowns(root_dir)

        if context.get("include_skills", True):
            skills_reg = self._leer_registry(base_dir / "skills" / "registry.json")
            result["skills"] = skills_reg
            if context.get("include_skill_docs", False):
                result["skill_docs"] = self._leer_skill_mds(base_dir / "skills" / "internos", skills_reg)

        if context.get("include_bots", True):
            result["bots"] = self._leer_registry(base_dir / "bots" / "registry.json")

        if context.get("include_agents", True):
            result["agents"] = self._leer_registry(base_dir / "agents" / "registry.json")

        if context.get("include_mcp", False):
            result["mcp"] = self._leer_registry(base_dir / "mcp" / "registry.json")

        return {"ok": True, "data": result}

    # --- markdowns ---

    def _leer_markdowns(self, root_dir: Path) -> dict[str, str]:
        docs: dict[str, str] = {}
        for md in sorted(root_dir.glob("*.md")):
            content = self._leer_archivo(md)
            if content is not None:
                docs[md.name] = content
        docs_dir = root_dir / "docs"
        if docs_dir.is_dir():
            for md in sorted(docs_dir.glob("*.md")):
                content = self._leer_archivo(md)
                if content is not None:
                    docs[f"docs/{md.name}"] = content
        return docs

    def _leer_skill_mds(self, internos_dir: Path, registry: dict) -> dict[str, str]:
        skill_docs: dict[str, str] = {}
        for nombre in registry:
            skill_md = internos_dir / nombre / "SKILL.md"
            content = self._leer_archivo(skill_md)
            if content is not None:
                skill_docs[nombre] = content
        return skill_docs

    # --- registries ---

    def _leer_registry(self, registry_path: Path) -> dict:
        if not registry_path.exists():
            return {}
        for encoding in ("utf-8", "utf-8-sig", "utf-16"):
            try:
                raw = registry_path.read_text(encoding=encoding).strip()
                return json.loads(raw) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        return {}

    # --- helpers ---

    def _leer_archivo(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
