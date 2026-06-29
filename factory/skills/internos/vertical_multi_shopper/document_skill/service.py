from __future__ import annotations

import base64
import importlib.util
import io
import re
from datetime import datetime
from pathlib import Path

from factory.engine import SupabaseClient


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _common():
    return _load(Path(__file__).resolve().parents[1] / "_common.py", "multi_shopper_common")


_XLSX_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/xlsx",
    "application/xls",
}

_EXTRACT_SCHEMA = {
    "supplier_name": None,
    "document_date": None,
    "currency": None,
    "products": [
        {
            "raw_description": None,
            "quantity": None,
            "unit": None,
            "unit_price": None,
            "subtotal": None,
            "brand": None,
            "category_name": None,
        }
    ],
    "summary": None,
}


def _xlsx_to_text(content_b64: str) -> str:
    try:
        import openpyxl
    except ImportError:
        return ""
    raw = base64.b64decode(content_b64)
    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    lines = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        lines.append(f"=== {sheet_name} ===")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            if any(c.strip() for c in cells):
                lines.append("\t".join(cells))
    return "\n".join(lines)


class DocumentSkillService:
    def ejecutar(self, context: dict) -> dict:
        action = context.get("action") or "list"
        if action == "extract":
            return self.extract(context)
        if action == "import_products":
            return self.import_products(context)
        if action == "create" and context.get("content_b64"):
            return self.upload_and_create(context)
        return _common().MultiShopperCrudService("documents").ejecutar(context)

    def upload_and_create(self, context: dict) -> dict:
        ctx_result = _common().resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        bucket = context.get("bucket") or context.get("storage_bucket")
        if not bucket:
            return {"ok": False, "error": "bucket/storage_bucket requerido para upload"}

        file_name = context.get("file_name") or context.get("filename") or "documento"
        safe_name = re.sub(r"[^\w.\-]", "_", file_name)
        path = context.get("storage_path") or f"{ctx['module_code']}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{safe_name}"

        storage_service = _load(
            Path(__file__).resolve().parents[2] / "vertical_supabase" / "supabase_storage_upload" / "service.py",
            "supabase_storage_upload_service",
        )
        uploaded = storage_service.StorageUploadService().ejecutar(
            {
                "bucket": bucket,
                "path": path,
                "content_b64": context.get("content_b64"),
                "content_type": context.get("file_type") or context.get("content_type") or "application/octet-stream",
            }
        )
        if not uploaded.get("ok"):
            return uploaded

        storage_data = uploaded.get("data") or {}

        # Para xlsx: extraer texto y guardarlo en extracted_text
        extracted_text = None
        file_type = context.get("file_type") or context.get("content_type") or ""
        is_xlsx = file_type in _XLSX_TYPES or file_name.lower().endswith((".xlsx", ".xls"))
        if is_xlsx:
            extracted_text = _xlsx_to_text(context.get("content_b64") or "")

        payload = {
            **ctx,
            "file_name": file_name,
            "file_url": storage_data.get("url"),
            "storage_bucket": bucket,
            "storage_path": storage_data.get("path"),
            "action": "create",
        }
        if extracted_text:
            payload["extracted_text"] = extracted_text

        result = _common().MultiShopperCrudService("documents").ejecutar(payload)
        if result.get("ok"):
            result["data"]["can_extract"] = bool(
                is_xlsx or file_type == "application/pdf" or (file_type or "").startswith("image/")
            )
        return result

    def extract(self, context: dict) -> dict:
        """Extrae productos de un documento guardado (por id/folio) o de content_b64 directo."""
        ctx_result = _common().resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        text = context.get("text") or context.get("extracted_text") or ""
        content_b64 = context.get("content_b64") or ""
        media_type = context.get("media_type") or context.get("file_type") or "text/plain"
        doc_id = None

        # Si se pasa id o folio, buscar el documento en la DB
        if not text and not content_b64:
            doc_id = context.get("id") or context.get("document_id")
            folio = context.get("folio")
            if not doc_id and not folio:
                return {"ok": False, "error": "Se requiere id, folio, content_b64 o text"}
            filters = {"company_id": ctx["company_id"]}
            if doc_id:
                filters["id"] = doc_id
            else:
                filters["folio"] = folio
            db_result = SupabaseClient(ctx).rest_select("documents", filters=filters, select="*", limit=1)
            if not db_result.get("ok"):
                return db_result
            rows = db_result.get("data") or []
            if not rows:
                return {"ok": False, "error": "Documento no encontrado"}
            doc = rows[0]
            doc_id = doc.get("id")
            text = doc.get("extracted_text") or ""
            media_type = doc.get("file_type") or "text/plain"
            if not text:
                return {"ok": False, "error": "El documento no tiene texto extraido. Solo se soporta extraccion de xlsx, PDF e imagenes."}

        ai_service = _load(
            Path(__file__).resolve().parents[2] / "vertical_factory_utils" / "ai_interpreter" / "service.py",
            "ai_interpreter_service",
        )
        ai_result = ai_service.run(
            {
                "mode": "extract",
                "schema": _EXTRACT_SCHEMA,
                "text": text,
                "content_b64": content_b64,
                "media_type": media_type,
                "context": (
                    "Extrae todos los productos listados en este documento de cotizacion. "
                    "Cada producto debe tener raw_description. "
                    "No inventes precios ni cantidades. Si no puedes leer un campo usa null."
                ),
            }
        )
        if not ai_result.get("ok"):
            return ai_result

        extracted = ai_result.get("data", {}).get("extracted") or {}

        # Guardar extracted_data en la tabla documents y marcar como procesado
        if doc_id and not context.get("dry_run", False):
            import json
            SupabaseClient(ctx).rest_update(
                "documents",
                {
                    "extracted_data": json.dumps(extracted),
                    "processing_status": "extracted",
                },
                {"id": doc_id, "company_id": ctx["company_id"]},
            )

        return {"ok": True, "data": {"extracted": extracted, "document_id": doc_id}}

    def import_products(self, context: dict) -> dict:
        """Crea productos en la DB a partir de la lista extraida por extract."""
        ctx_result = _common().resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        products = context.get("products") or []
        if not products:
            return {"ok": False, "error": "products requerido (lista de productos a importar)"}

        dry_run = context.get("dry_run", True)
        created = []
        errors = []
        crud = _common().MultiShopperCrudService("products")

        for item in products:
            raw_description = str(item.get("raw_description") or item.get("canonical_name") or "").strip()
            if not raw_description:
                continue
            payload = {
                **ctx,
                "action": "create",
                "canonical_name": raw_description,
                "category_name": item.get("category_name") or None,
                "unit": item.get("unit") or None,
                "brand": item.get("brand") or None,
                "dry_run": dry_run,
            }
            result = crud.ejecutar(payload)
            if result.get("ok"):
                created.append(result.get("data", {}).get("product") or {"canonical_name": raw_description})
            else:
                errors.append({"item": raw_description, "error": result.get("error")})

        return {
            "ok": True,
            "data": {
                "created": len(created),
                "errors": len(errors),
                "products": created,
                "error_detail": errors,
                "dry_run": dry_run,
            },
        }
