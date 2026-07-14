from __future__ import annotations

import importlib.util
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[1]
_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def blank(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def customer_key(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_date(value: Any, field: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        raise ValueError(f"{field} debe tener formato YYYY-MM-DD")


def schema_identifier(context: dict) -> str:
    schema = str(
        context.get("schema")
        or context.get("followup_schema")
        or context.get("billing_schema")
        or context.get("supabase_schema")
        or ""
    ).strip()
    if not _VALID_SCHEMA.match(schema):
        raise ValueError("schema/followup_schema invalido o requerido")
    return schema


def resolve_followup_context(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}

    direct = {
        "schema": str(
            context.get("schema")
            or context.get("followup_schema")
            or context.get("billing_schema")
            or context.get("supabase_schema")
            or ""
        ).strip(),
        "company_id": str(context.get("company_id") or context.get("empresa_id") or "").strip(),
        "project_code": str(context.get("project_code") or "").strip(),
        "module_code": str(context.get("module_code") or "").strip(),
    }
    if all(direct.values()):
        return {
            "ok": True,
            "data": {
                **context,
                **direct,
                "empresa_id": direct["company_id"],
                "followup_schema": direct["schema"],
            },
        }

    service_path = _SKILLS_ROOT / "vertical_erp" / "erp_project_context_resolve" / "service.py"
    spec = importlib.util.spec_from_file_location("erp_project_context_resolve_service", service_path)
    if spec is None or spec.loader is None:
        return {"ok": False, "error": "no se pudo cargar erp_project_context_resolve"}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.ErpProjectContextResolveService().ejecutar(context)
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error") or "contexto ERP incompleto"}

    data = result.get("data") or {}
    resolved = {
        "schema": str(context.get("followup_schema") or context.get("billing_schema") or data.get("schema") or "").strip(),
        "company_id": str(data.get("company_id") or data.get("empresa_id") or context.get("company_id") or "").strip(),
        "project_code": str(data.get("project_code") or context.get("project_code") or "").strip(),
        "module_code": str(data.get("module_code") or context.get("module_code") or "").strip(),
    }
    missing = [key for key, value in resolved.items() if not value]
    if missing:
        return {"ok": False, "error": f"contexto ERP followup incompleto: {', '.join(missing)}"}

    return {
        "ok": True,
        "data": {
            **context,
            **resolved,
            "empresa_id": resolved["company_id"],
            "followup_schema": resolved["schema"],
        },
    }


def identity_row(context: dict) -> dict:
    company_id = context.get("company_id") or context.get("empresa_id")
    return {
        "empresa_id": company_id,
        "project_code": context.get("project_code"),
        "module_code": context.get("module_code"),
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
