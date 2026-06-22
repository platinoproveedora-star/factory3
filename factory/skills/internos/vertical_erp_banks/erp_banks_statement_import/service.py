from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _banks_common import SupabaseClient, blank, resolve_banks_context  # noqa: E402


def _text(v: Any) -> str:
    return str(v or "").strip()


class ErpBanksStatementImportService:
    def ejecutar(self, context: dict) -> dict:
        banks_schema = _text(context.get("banks_schema") or context.get("schema"))
        statements_schema = _text(context.get("statements_schema"))
        if not statements_schema:
            return {"ok": False, "error": "statements_schema requerido"}

        ctx_result = resolve_banks_context({**context, "schema": banks_schema})
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        extraction_id = _text(context.get("extraction_id"))
        if not extraction_id:
            return {"ok": False, "error": "extraction_id requerido"}

        account_id = _text(context.get("account_id"))
        account_folio = _text(context.get("account_folio"))
        if not account_id and not account_folio:
            return {"ok": False, "error": "account_id o account_folio requerido"}

        line_ids: list[str] = [str(i) for i in (context.get("line_ids") or []) if i]
        dry_run = bool(context.get("dry_run", True))

        stmt_db = SupabaseClient({"schema": statements_schema})
        filters: dict = {
            "extraction_id": f"eq.{extraction_id}",
            "empresa_id": f"eq.{ctx['company_id']}",
        }
        if line_ids:
            filters["id"] = "in.(" + ",".join(line_ids) + ")"

        lines_result = stmt_db.rest_select(
            "statement_extracted_lines",
            filters=filters,
            select="id,folio,raw_line_order,line_date,direction,amount,clave_rastreo,referencia,description,metadata",
            order="raw_line_order.asc",
            limit=2000,
        )
        if not lines_result.get("ok"):
            return lines_result

        lines = lines_result.get("data") or []
        if not lines:
            return {"ok": False, "error": "No se encontraron líneas para importar"}

        if dry_run:
            return {
                "ok": True,
                "message": f"dry_run: se importarían {len(lines)} líneas",
                "data": {"lines_to_import": len(lines), "extraction_id": extraction_id},
            }

        banks_db = SupabaseClient(ctx)
        results = []
        imported = 0
        skipped = 0
        errors = 0

        for line in lines:
            movement_type = "entrada" if line.get("direction") == "deposito" else "salida"
            params = {
                "p_account_id": account_id or None,
                "p_account_folio": account_folio or None,
                "p_movement_type": movement_type,
                "p_source_type": "corte",
                "p_source_module": "bank_statement",
                "p_source_id": line["id"],
                "p_source_folio": blank(line.get("folio")),
                "p_amount": float(line.get("amount") or 0),
                "p_movement_date": line.get("line_date"),
                "p_clave_rastreo": blank(line.get("clave_rastreo")),
                "p_notes": blank(line.get("description")),
                "p_metadata": {
                    "statement_line_id": line["id"],
                    "raw_line_order": line.get("raw_line_order"),
                    "referencia": line.get("referencia"),
                    **(line.get("metadata") or {}),
                },
                "p_empresa_id": ctx["company_id"],
                "p_project_code": ctx["project_code"],
                "p_module_code": ctx["module_code"],
            }
            rpc_result = banks_db.rpc("banks_record_movement", params)
            if not rpc_result.get("ok"):
                errors += 1
                results.append({"line_id": line["id"], "status": "error", "error": rpc_result.get("error")})
                continue

            rpc_data = rpc_result.get("data") or {}
            if isinstance(rpc_data, list) and rpc_data:
                rpc_data = rpc_data[0]
            inner = rpc_data.get("data", rpc_data) if isinstance(rpc_data, dict) else {}
            movement = inner.get("movement", {}) if isinstance(inner, dict) else {}
            is_idempotent = bool(inner.get("idempotent")) if isinstance(inner, dict) else False

            if is_idempotent:
                skipped += 1
                results.append({"line_id": line["id"], "status": "exists", "folio": movement.get("folio")})
            else:
                imported += 1
                results.append({"line_id": line["id"], "status": "imported", "folio": movement.get("folio")})

        return {
            "ok": True,
            "data": {
                "imported": imported,
                "skipped": skipped,
                "errors": errors,
                "total": len(lines),
                "results": results,
            },
        }
