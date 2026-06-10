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
    schema = str(context.get("schema") or context.get("billing_schema") or context.get("supabase_schema") or "").strip()
    if not _VALID_SCHEMA.match(schema):
        raise ValueError("schema/billing_schema invalido o requerido")
    return schema


def resolve_billing_context(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    direct = {
        "schema": str(context.get("schema") or context.get("billing_schema") or context.get("supabase_schema") or "").strip(),
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
                "billing_schema": direct["schema"],
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
        return {"ok": False, "error": result.get("error") or "contexto ERP billing incompleto"}
    data = result.get("data") or {}
    schema = str(context.get("billing_schema") or data.get("schema") or "").strip()
    company_id = str(data.get("company_id") or data.get("empresa_id") or "").strip()
    project_code = str(data.get("project_code") or "").strip()
    module_code = str(data.get("module_code") or "").strip()
    missing = [
        key
        for key, value in {
            "schema": schema,
            "company_id": company_id,
            "project_code": project_code,
            "module_code": module_code,
        }.items()
        if not value
    ]
    if missing:
        return {"ok": False, "error": f"contexto ERP billing incompleto: {', '.join(missing)}"}
    return {
        "ok": True,
        "data": {
            **context,
            "schema": schema,
            "billing_schema": schema,
            "company_id": company_id,
            "empresa_id": company_id,
            "project_code": project_code,
            "module_code": module_code,
            "sales_schema": data.get("sales_schema") or context.get("sales_schema") or context.get("schema_ventas"),
            "inventory_schema": data.get("inventory_schema") or context.get("inventory_schema") or context.get("schema_inventario"),
            "module_schemas": data.get("module_schemas") or {},
            "module_projects": data.get("module_projects") or {},
        },
    }


def sales_context(context: dict) -> dict:
    schema = str(context.get("sales_schema") or context.get("schema_ventas") or "").strip()
    if not schema:
        module_schemas = context.get("module_schemas") if isinstance(context.get("module_schemas"), dict) else {}
        schema = str(module_schemas.get("ventas") or "").strip()
    if not schema:
        return {"ok": False, "error": "sales_schema/schema_ventas requerido para aplicar pago a documento de ventas"}
    return {
        "ok": True,
        "data": {
            **context,
            "schema": schema,
            "company_id": context.get("company_id") or context.get("empresa_id"),
            "empresa_id": context.get("empresa_id") or context.get("company_id"),
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


def insert_event(context: dict, event_type: str, payload: dict, dry_run: bool) -> None:
    if dry_run:
        return
    db = SupabaseClient(context)
    folio_result = reserve_folio(context, "billing_events", "BEVT")
    if not folio_result.get("ok"):
        return
    db.rest_insert(
        "billing_events",
        {
            "folio": folio_result["data"]["folio"],
            **identity_row(context),
            "event_type": event_type,
            "payload": payload,
        },
    )
