"""Service for add_agent_memory_supabase - adds Supabase memory to an agent."""

from __future__ import annotations

import json
import re
from pathlib import Path

from factory.engine import SupabaseClient

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


class AddAgentMemorySupabaseService:

    def ejecutar(self, context: dict) -> dict:
        ok, error = self._validar(context)
        if not ok:
            return {"ok": False, "error": error}

        base_dir = Path(context.get("base_dir", "factory"))
        agent_name = context["agent_name"]
        table_name = context.get("table_name", "agent_memory")
        agent_path = base_dir / "agents" / agent_name
        manifest_path = agent_path / "manifest.json"
        memory_path = agent_path / "agent_memory.py"
        sql = self._memory_table_sql(table_name)

        plan = {
            "agent_name": agent_name,
            "table_name": table_name,
            "agent_path": str(agent_path),
            "manifest_path": str(manifest_path),
            "memory_path": str(memory_path),
            "sql": sql,
        }
        if context.get("dry_run", True):
            return {"ok": True, "message": "plan de memoria Supabase generado; no se escribio nada", "data": plan}

        if not agent_path.exists():
            return {"ok": False, "error": f"agente no existe: {agent_name}", "data": plan}

        table_result = SupabaseClient(context).management_query(sql)
        if not table_result.get("ok"):
            table_result["data"] = {**table_result.get("data", {}), **plan}
            return table_result

        memory_path.write_text(self._memory_module(table_name), encoding="utf-8")
        manifest = self._load_json(manifest_path)
        manifest["memory"] = {
            "provider": "supabase",
            "entrypoint": "agent_memory.py",
            "table": table_name,
            "requires_env": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"],
        }
        self._write_json(manifest_path, manifest)
        return {"ok": True, "message": "memoria Supabase agregada al agente", "data": plan}

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        agent_name = context.get("agent_name")
        table_name = context.get("table_name", "agent_memory")
        if not agent_name or not _VALID_NAME.match(str(agent_name)):
            return False, "agent_name invalido o requerido"
        if not table_name or not re.match(r"^[a-z][a-z0-9_]*$", str(table_name)):
            return False, "table_name debe ser snake_case"
        return True, None

    def _memory_table_sql(self, table_name: str) -> str:
        return f"""
create table if not exists {table_name} (
  id uuid primary key default gen_random_uuid(),
  agent_name text not null,
  user_id text not null,
  memory_type text default 'fact',
  content text not null,
  metadata jsonb default '{{}}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists {table_name}_agent_user_idx on {table_name} (agent_name, user_id);
""".strip()

    def _memory_module(self, table_name: str) -> str:
        return f'''"""Supabase-backed memory for this Factory agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from factory.engine import SupabaseClient

TABLE_NAME = "{table_name}"
AGENT_NAME = Path(__file__).resolve().parent.name


def search(query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = context or {{}}
    user_id = str(ctx.get("user_id") or ctx.get("chat_id") or "default")
    result = SupabaseClient(ctx).rest_select(
        TABLE_NAME,
        filters={{"agent_name": AGENT_NAME, "user_id": user_id}},
        select="id,memory_type,content,metadata,created_at,updated_at",
        limit=int(ctx.get("memory_limit", 8)),
        order="updated_at.desc",
    )
    if not result.get("ok"):
        return result
    memories = result.get("data") or []
    text = (query or "").lower()
    if text:
        memories = [
            item for item in memories
            if text in str(item.get("content", "")).lower() or not query
        ] or memories
    return {{"ok": True, "data": {{"memories": memories[: int(ctx.get("memory_limit", 8))]}}}}


def remember(user_message: str, assistant_response: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = context or {{}}
    content = _memory_content(user_message, assistant_response)
    if not content:
        return {{"ok": True, "message": "sin memoria relevante", "data": {{}}}}
    user_id = str(ctx.get("user_id") or ctx.get("chat_id") or "default")
    row = {{
        "agent_name": AGENT_NAME,
        "user_id": user_id,
        "memory_type": ctx.get("memory_type", "fact"),
        "content": content,
        "metadata": {{"source": ctx.get("source", "agent")}},
    }}
    return SupabaseClient(ctx).rest_insert(TABLE_NAME, row)


def _memory_content(user_message: str, assistant_response: str) -> str:
    text = (user_message or "").strip()
    if len(text) < 12:
        return ""
    lowered = text.lower()
    question_starts = ("como ", "cual ", "cuál ", "que ", "qué ", "cuando ", "cuándo ", "donde ", "dónde ")
    if "?" in lowered or lowered.startswith(question_starts):
        return ""
    signals = (
        "recuerda",
        "guarda",
        "guardar",
        "guárd",
        "memoria",
        "mi ",
        "soy ",
        "tengo ",
        "prefiero ",
        "cliente ",
        "negocio ",
        "entrada ",
        "salida ",
        "producto ",
        "inventario ",
        "stock ",
    )
    if any(signal in lowered for signal in signals):
        return text[:1000]
    return ""
'''

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8-sig", errors="replace").strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _write_json(self, path: Path, data: dict) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
