from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _common():
    return _load(Path(__file__).resolve().parents[1] / "_common.py", "multi_shopper_common")


class DocumentSkillService:
    def ejecutar(self, context: dict) -> dict:
        action = context.get("action") or "list"
        if action == "extract":
            return self.extract(context)
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
        path = context.get("storage_path") or f"{ctx['module_code']}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file_name}"
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
        data = uploaded.get("data") or {}
        payload = {
            **ctx,
            "file_name": file_name,
            "file_url": data.get("url"),
            "storage_bucket": bucket,
            "storage_path": data.get("path"),
            "action": "create",
        }
        return _common().MultiShopperCrudService("documents").ejecutar(payload)

    def extract(self, context: dict) -> dict:
        ai_service = _load(
            Path(__file__).resolve().parents[2] / "vertical_factory_utils" / "ai_interpreter" / "service.py",
            "ai_interpreter_service",
        )
        schema = {
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
        result = ai_service.run(
            {
                "mode": "extract",
                "schema": schema,
                "text": context.get("text") or context.get("extracted_text") or "",
                "content_b64": context.get("content_b64") or "",
                "media_type": context.get("media_type") or context.get("file_type") or "text/plain",
                "context": (
                    "Extrae productos para cotizacion de compra/venta. "
                    "No inventes precios ni cantidades. Si no puedes leer un campo usa null."
                ),
            }
        )
        if not result.get("ok"):
            return result
        extracted = result.get("data", {}).get("extracted") or {}
        return {"ok": True, "data": {"extracted": extracted}}
