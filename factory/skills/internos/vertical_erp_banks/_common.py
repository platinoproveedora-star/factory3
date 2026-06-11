from __future__ import annotations

import importlib.util
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[1]
_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")


def blank(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def money(value: Any) -> float:
    return round(float(value or 0), 2)


def today_iso() -> str:
    return date.today().isoformat()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def schema_identifier(context: dict) -> str:
    schema = str(context.get("schema") or context.get("banks_schema") or context.get("supabase_schema") or "").strip()
    if not _VALID_SCHEMA.match(schema):
        raise ValueError("schema/banks_schema invalido o requerido")
    return schema


def resolve_banks_context(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    schema = str(context.get("banks_schema") or context.get("schema") or context.get("supabase_schema") or "").strip()
    company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
    project_code = str(context.get("banks_project_code") or context.get("project_code") or "").strip()
    module_code = str(context.get("banks_module_code") or context.get("module_code") or "banks").strip()
    missing = [k for k, v in {"banks_schema": schema, "company_id": company_id, "project_code": project_code}.items() if not v]
    if missing:
        return {"ok": False, "error": f"contexto ERP banks incompleto: {', '.join(missing)}"}
    return {
        "ok": True,
        "data": {
            **context,
            "schema": schema,
            "banks_schema": schema,
            "company_id": company_id,
            "empresa_id": company_id,
            "project_code": project_code,
            "module_code": module_code,
        },
    }


def reserve_folio(context: dict, table: str, prefix: str, digits: int = 5) -> dict:
    service_path = _SKILLS_ROOT / "vertical_erp" / "erp_folio_reserve" / "service.py"
    spec = importlib.util.spec_from_file_location("erp_folio_reserve_service", service_path)
    if spec is None or spec.loader is None:
        return {"ok": False, "error": "no se pudo cargar erp_folio_reserve"}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ErpFolioReserveService().ejecutar(
        {
            **context,
            "dry_run": False,
            "table": table,
            "scope": table,
            "prefix": prefix,
            "folio_column": "folio",
            "digits": digits,
        }
    )


def identity_row(context: dict) -> dict:
    company_id = context.get("company_id") or context.get("empresa_id")
    return {
        "empresa_id": company_id,
        "project_code": context.get("project_code"),
        "module_code": context.get("module_code"),
    }


def fetch_one(db: SupabaseClient, table: str, filters: dict, select: str = "*") -> dict | None:
    result = db.rest_select(table, filters=filters, select=select, limit=1)
    if not result.get("ok"):
        raise RuntimeError(result.get("error") or f"error leyendo {table}")
    rows = result.get("data") or []
    return rows[0] if rows else None
