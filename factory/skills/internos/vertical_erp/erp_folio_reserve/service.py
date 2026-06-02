from __future__ import annotations

import re

from factory.engine import SupabaseClient


_VALID_SCOPE = re.compile(r"^[a-z0-9_]{2,80}$")
_VALID_PREFIX = re.compile(r"^[A-Z0-9_]{2,12}$")


class ErpFolioReserveService:
    def ejecutar(self, context: dict) -> dict:
        scope = str(context.get("scope") or context.get("table") or "").strip().lower()
        prefix = str(context.get("prefix") or "").strip().upper()
        digits = int(context.get("digits") or 5)
        if not _VALID_SCOPE.match(scope):
            return {"ok": False, "error": "scope invalido"}
        if not _VALID_PREFIX.match(prefix):
            return {"ok": False, "error": "prefix invalido"}
        if digits < 1 or digits > 12:
            return {"ok": False, "error": "digits debe estar entre 1 y 12"}

        schema_context = self._schema_context(context)
        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se reservo folio",
                "data": {"folio": f"{prefix}-DRYRUN", "scope": scope, "prefix": prefix, "digits": digits},
            }

        min_current = self._current_max(schema_context, context, prefix)
        result = SupabaseClient(schema_context).rpc(
            "reserve_erp_folio",
            {
                "p_scope": scope,
                "p_prefix": prefix,
                "p_digits": digits,
                "p_empresa_id": schema_context.get("company_id") or schema_context.get("empresa_id"),
                "p_project_code": schema_context.get("project_code"),
                "p_module_code": schema_context.get("module_code"),
                "p_min_current": min_current,
            },
        )
        if not result.get("ok"):
            return result

        folio = result.get("data")
        if isinstance(folio, list) and folio:
            folio = folio[0]
        if isinstance(folio, dict):
            folio = folio.get("reserve_erp_folio") or folio.get("folio")
        if not isinstance(folio, str) or not folio:
            return {"ok": False, "error": "Supabase no devolvio folio", "data": result.get("data")}

        return {"ok": True, "data": {"folio": folio, "scope": scope, "prefix": prefix, "digits": digits}}

    def _current_max(self, schema_context: dict, context: dict, prefix: str) -> int:
        table = str(context.get("table") or "").strip()
        folio_column = str(context.get("folio_column") or "folio").strip()
        if not re.match(r"^[a-z][a-z0-9_]*$", table):
            return 0
        if not re.match(r"^[a-z][a-z0-9_]*$", folio_column):
            return 0
        result = SupabaseClient(schema_context).rest_select(
            table,
            filters={folio_column: f"ilike.{prefix}-%"},
            select=folio_column,
            limit=int(context.get("scan_limit") or 10000),
        )
        if not result.get("ok"):
            return 0
        numbers = []
        for row in result.get("data") or []:
            text = str(row.get(folio_column) or "")
            match = re.match(rf"^{re.escape(prefix)}-(\d+)$", text)
            if match:
                numbers.append(int(match.group(1)))
        return max(numbers or [0])

    def _schema_context(self, context: dict) -> dict:
        return {
            **context,
            "schema": context.get("schema") or context.get("supabase_schema") or "uc101_proy004",
            "company_id": context.get("company_id") or context.get("empresa_id") or "EMP_DURALON",
            "project_code": context.get("project_code") or "PROY-004",
            "module_code": context.get("module_code") or "inventario",
        }
