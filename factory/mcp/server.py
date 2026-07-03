"""
Factory3 MCP Bridge.

Thin bridge between Hermes (or any MCP client) and Factory3 skills.
It does not execute skills directly and does not talk to Supabase. It reads
the skill registry for discovery, then delegates execution to the existing
Factory API endpoint:

    POST /run/{skill_name}

Required environment variables:
    FACTORY_API_URL     Base URL for factory_api.py, for example
                        https://your-factory-api.example.com
    FACTORY_RUN_SECRET  Same secret configured on Factory API Render service.

Optional:
    REGISTRY_PATH       Local path to factory/skills/registry.json. If omitted,
                        this file defaults to ../skills/registry.json relative
                        to this server.py. If that does not exist, it falls
                        back to the raw GitHub registry.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP


FACTORY_API_URL = os.getenv("FACTORY_API_URL", "").rstrip("/")
FACTORY_RUN_SECRET = os.getenv("FACTORY_RUN_SECRET", "")
REGISTRY_PATH = os.getenv("REGISTRY_PATH", "")

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "skills" / "registry.json"
RAW_REGISTRY_URL = (
    "https://raw.githubusercontent.com/"
    "platinoproveedora-star/factory3/main/factory/skills/registry.json"
)

if not FACTORY_API_URL:
    raise RuntimeError("Falta variable de entorno FACTORY_API_URL")

mcp = FastMCP("factory3")


def _load_registry() -> dict[str, Any]:
    candidates: list[Path] = []
    if REGISTRY_PATH:
        candidates.append(Path(REGISTRY_PATH))
    candidates.append(DEFAULT_REGISTRY_PATH)

    for path in candidates:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}

    response = httpx.get(RAW_REGISTRY_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {}


_REGISTRY_CACHE: dict[str, Any] | None = None


def _registry() -> dict[str, Any]:
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        _REGISTRY_CACHE = _load_registry()
    return _REGISTRY_CACHE


@mcp.tool()
def list_verticals() -> list[str]:
    """List all available Factory3 verticals."""
    verticals = {
        str(meta.get("vertical") or "?")
        for meta in _registry().values()
        if isinstance(meta, dict)
    }
    return sorted(verticals)


@mcp.tool()
def list_skills(vertical: str | None = None) -> list[dict[str, Any]]:
    """List available skills, optionally filtered by vertical."""
    out: list[dict[str, Any]] = []
    for name, meta in _registry().items():
        if not isinstance(meta, dict):
            continue
        if vertical and meta.get("vertical") != vertical:
            continue
        out.append(
            {
                "name": name,
                "vertical": meta.get("vertical"),
                "descripcion": meta.get("descripcion", ""),
                "kind": meta.get("kind", "executable"),
            }
        )
    return sorted(out, key=lambda item: item["name"])


@mcp.tool()
def search_skills(query: str) -> list[dict[str, Any]]:
    """Search skills by keyword in name or description."""
    q = str(query or "").lower()
    out: list[dict[str, Any]] = []
    for name, meta in _registry().items():
        if not isinstance(meta, dict):
            continue
        haystack = f"{name} {meta.get('descripcion', '')}".lower()
        if q in haystack:
            out.append(
                {
                    "name": name,
                    "vertical": meta.get("vertical"),
                    "descripcion": meta.get("descripcion", ""),
                }
            )
    return sorted(out, key=lambda item: item["name"])


@mcp.tool()
def get_skill_manifest(skill_name: str) -> dict[str, Any]:
    """Return registry metadata for a skill."""
    meta = _registry().get(skill_name)
    if not isinstance(meta, dict):
        return {"error": f"Skill no encontrado en registry: {skill_name}"}
    return meta


@mcp.tool()
def run_skill(skill_name: str, context: dict[str, Any]) -> dict[str, Any]:
    """Run a Factory3 skill through Factory API /run/{skill_name}."""
    if skill_name not in _registry():
        return {"ok": False, "error": f"Skill no encontrado en registry: {skill_name}"}
    if not FACTORY_RUN_SECRET:
        return {"ok": False, "error": "FACTORY_RUN_SECRET requerido para ejecutar skills via MCP"}
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}

    headers = {"Authorization": f"Bearer {FACTORY_RUN_SECRET}"}
    url = f"{FACTORY_API_URL}/run/{skill_name}"
    try:
        response = httpx.post(url, json=context, headers=headers, timeout=60)
    except httpx.HTTPError as exc:
        return {"ok": False, "error": f"Fallo de red llamando a {url}: {exc}"}

    if response.status_code == 403:
        return {"ok": False, "error": "Skill de uso interno, no accesible via MCP"}
    if response.status_code == 401:
        return {"ok": False, "error": "FACTORY_RUN_SECRET invalido o faltante"}

    try:
        return response.json()
    except ValueError:
        return {
            "ok": False,
            "error": f"Respuesta no-JSON, status {response.status_code}: {response.text[:300]}",
        }


if __name__ == "__main__":
    mcp.run()
