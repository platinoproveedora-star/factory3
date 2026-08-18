from __future__ import annotations

import base64
import importlib.util
import io
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "stock4all"
_BUCKET = "stock4all-purchase-docs"

_EXCEL_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}

_EXTRACT_SCHEMA = {
    "proveedor": "nombre del proveedor o vendedor que aparece en el documento",
    "fecha": "fecha del documento, formato YYYY-MM-DD",
    "folio_proveedor": "numero de factura, folio o referencia del documento",
    "items": (
        "arreglo de renglones de compra; cada elemento debe ser un objeto con: "
        "producto (nombre o descripcion tal como aparece en el documento), "
        "sku (clave, codigo o numero de parte del proveedor/fabricante para ese producto, tal como "
        "aparece en el documento -- suele ser una columna separada del nombre; usa null si no existe), "
        "cantidad (numero), costo_unitario (numero, precio unitario SIN IVA si se puede distinguir), "
        "unidad (unidad de medida si aparece, ej. pieza, kg, rollo, metro)"
    ),
}

_EXTRACT_CONTEXT = (
    "Eres un asistente que lee documentos de compra (facturas, notas de remision, cotizaciones) "
    "de una empresa de materiales de construccion en Mexico, incluyendo tuberia. Extrae TODOS los "
    "renglones de productos comprados con su cantidad y costo unitario. Estos documentos casi siempre "
    "traen una columna de clave/codigo/SKU del proveedor separada del nombre del producto -- captura "
    "ese valor en el campo sku de cada renglon, no lo mezcles con el nombre del producto. Si el "
    "documento desglosa IVA, usa el costo unitario SIN IVA. Si un campo no se puede determinar usa null."
)


class ErpComprasPurchaseDraftService:
    def ejecutar(self, context: dict) -> dict:
        action = str(context.get("action") or "list").strip()
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}

        if action == "upload_extract":
            return self._upload_extract(context, company_id)
        if action == "list":
            return self._list(context, company_id)
        if action == "update":
            return self._update(context, company_id)
        if action == "delete":
            return self._delete(context, company_id)
        if action == "confirm":
            return self._confirm(context, company_id)
        return {"ok": False, "error": f"action invalido: {action}. Usa upload_extract|list|update|delete|confirm"}

    def _db(self) -> SupabaseClient:
        return SupabaseClient({"schema": _SCHEMA})

    # ---------------------------------------------------------------- upload_extract

    def _upload_extract(self, context: dict, company_id: str) -> dict:
        content_b64 = str(context.get("content_b64") or "").strip()
        media_type = str(context.get("media_type") or "").strip()
        filename = str(context.get("filename") or "documento").strip()
        source_schema = str(context.get("source_schema") or "").strip()
        source_project_code = str(context.get("source_project_code") or "").strip()
        warehouse_id = context.get("warehouse_id")
        if not content_b64:
            return {"ok": False, "error": "content_b64 requerido"}
        if not media_type:
            return {"ok": False, "error": "media_type requerido"}
        if not source_schema:
            return {"ok": False, "error": "source_schema requerido"}

        upload = self._upload_file(company_id, filename, content_b64, media_type)
        if not upload.get("ok"):
            return upload
        file_url = upload["data"]["file_url"]

        extraction = self._extract(content_b64, media_type, filename)
        if not extraction.get("ok"):
            return {"ok": False, "error": extraction.get("error"), "data": {"file_url": file_url}}
        extracted = extraction["data"]

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se guardo el borrador (archivo si se subio)",
                "data": {"file_url": file_url, "extracted": extracted},
            }

        row = {
            "company_id": company_id,
            "source_schema": source_schema,
            "source_project_code": source_project_code or None,
            "warehouse_id": warehouse_id or None,
            "status": "draft",
            "file_name": filename,
            "file_url": file_url,
            "media_type": media_type,
            "extracted_json": extracted,
            "supplier_name_hint": (extracted or {}).get("proveedor"),
        }
        result = self._db().rest_insert("purchase_drafts", row)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        return {"ok": True, "data": {"draft": data[0] if data else None}}

    def _upload_file(self, company_id: str, filename: str, content_b64: str, media_type: str) -> dict:
        import os

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}
        try:
            file_bytes = base64.b64decode(content_b64)
        except Exception:
            return {"ok": False, "error": "content_b64 invalido"}

        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
        ts = int(time.time() * 1000)
        path = f"{company_id}/{ts}_{safe_name}"
        req = urllib.request.Request(
            f"{url}/storage/v1/object/{_BUCKET}/{path}",
            data=file_bytes,
            method="POST",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": media_type,
                "x-upsert": "true",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}"}
        file_url = f"{url}/storage/v1/object/public/{_BUCKET}/{path}"
        return {"ok": True, "data": {"file_url": file_url, "storage_path": path}}

    def _extract(self, content_b64: str, media_type: str, filename: str) -> dict:
        if media_type in _EXCEL_TYPES or filename.lower().endswith((".xlsx", ".xls")):
            text_result = self._excel_to_text(content_b64)
            if not text_result.get("ok"):
                return text_result
            ai_content_b64 = base64.b64encode(text_result["data"]["text"].encode("utf-8")).decode("ascii")
            ai_media_type = "text/plain"
        elif media_type == "application/pdf" or media_type.startswith("image/"):
            ai_content_b64 = content_b64
            ai_media_type = media_type
        else:
            return {"ok": False, "error": f"media_type no soportado para extraccion: {media_type}"}

        ai = self._ai_interpreter()
        result = ai.run({
            "mode": "extract",
            "schema": _EXTRACT_SCHEMA,
            "content_b64": ai_content_b64,
            "media_type": ai_media_type,
            "context": _EXTRACT_CONTEXT,
            "max_tokens": 4096,
        })
        if not result.get("ok"):
            return result
        return {"ok": True, "data": result["data"]["extracted"]}

    def _excel_to_text(self, content_b64: str) -> dict:
        try:
            import openpyxl
        except ImportError:
            return {"ok": False, "error": "openpyxl no disponible"}
        try:
            file_bytes = base64.b64decode(content_b64)
            workbook = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        except Exception as exc:
            return {"ok": False, "error": f"no se pudo leer el excel: {exc}"}

        lines = []
        for sheet in workbook.worksheets:
            lines.append(f"# hoja: {sheet.title}")
            for row_index, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                if row_index > 300:
                    lines.append("... (truncado)")
                    break
                cells = ["" if v is None else str(v) for v in row]
                if any(c.strip() for c in cells):
                    lines.append(" | ".join(cells))
        text = "\n".join(lines)
        return {"ok": True, "data": {"text": text[:60000]}}

    def _ai_interpreter(self):
        module_path = Path(__file__).resolve().parents[2] / "vertical_factory_utils" / "ai_interpreter" / "service.py"
        spec = importlib.util.spec_from_file_location("ai_interpreter_service", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # ---------------------------------------------------------------- list / update / delete

    def _list(self, context: dict, company_id: str) -> dict:
        status = str(context.get("status") or "").strip()
        filters = {"company_id": company_id}
        if status:
            filters["status"] = status
        result = self._db().rest_select(
            "purchase_drafts",
            filters=filters,
            select="*",
            order="created_at.desc",
            limit=int(context.get("limit") or 50),
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"drafts": result.get("data") or []}}

    def _update(self, context: dict, company_id: str) -> dict:
        draft_id = str(context.get("id") or "").strip()
        if not draft_id:
            return {"ok": False, "error": "id requerido"}
        values = {}
        for key in ("extracted_json", "notes", "warehouse_id", "status"):
            if key in context:
                values[key] = context[key]
        if not values:
            return {"ok": False, "error": "nada que actualizar"}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se actualizo", "data": {"values": values}}
        result = self._db().rest_update("purchase_drafts", values, {"id": draft_id, "company_id": company_id})
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        return {"ok": True, "data": {"draft": data[0] if data else None}}

    def _delete(self, context: dict, company_id: str) -> dict:
        draft_id = str(context.get("id") or "").strip()
        if not draft_id:
            return {"ok": False, "error": "id requerido"}
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se borro"}

        existing = self._db().rest_select("purchase_drafts", filters={"id": draft_id, "company_id": company_id}, select="file_url", limit=1)
        if existing.get("ok"):
            rows = existing.get("data") or []
            if rows and rows[0].get("file_url"):
                self._delete_file(rows[0]["file_url"])

        result = self._db().rest_delete("purchase_drafts", {"id": draft_id, "company_id": company_id})
        if not result.get("ok"):
            return result
        return {"ok": True, "message": "borrador eliminado"}

    def _delete_file(self, file_url: str) -> None:
        import os

        marker = f"/object/public/{_BUCKET}/"
        idx = file_url.find(marker)
        if idx < 0:
            return
        path = file_url[idx + len(marker):]
        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return
        req = urllib.request.Request(
            f"{url}/storage/v1/object/{_BUCKET}/{path}",
            method="DELETE",
            headers={"apikey": key, "Authorization": f"Bearer {key}", "User-Agent": "FactoryFactory/0.1 (+https://github.com/)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp.read()
        except Exception:
            pass  # el borrado del borrador no debe fallar por un archivo huerfano

    # ---------------------------------------------------------------- confirm

    def _confirm(self, context: dict, company_id: str) -> dict:
        draft_id = str(context.get("id") or "").strip()
        purchase_ctx = {
            "company_id": company_id,
            "schema": context.get("source_schema"),
            "project_code": context.get("source_project_code"),
            "supplier_id": context.get("supplier_id"),
            "movement_date": context.get("movement_date"),
            "external_folio": context.get("external_folio"),
            "paid_amount": context.get("paid_amount"),
            "notes": context.get("notes"),
            "warehouse_id": context.get("warehouse_id"),
            "items": context.get("items"),
            "dry_run": context.get("dry_run", True),
        }
        result = self._purchase_create(purchase_ctx)
        if not result.get("ok"):
            return result

        if draft_id and not context.get("dry_run", True):
            purchase = (result.get("data") or {}).get("purchase") or {}
            self._db().rest_update(
                "purchase_drafts",
                {"status": "confirmed", "confirmed_purchase_folio": purchase.get("source_folio")},
                {"id": draft_id, "company_id": company_id},
            )
        return result

    def _purchase_create(self, context: dict) -> dict:
        module_path = Path(__file__).resolve().parents[1] / "erp_compras_purchase_create" / "service.py"
        spec = importlib.util.spec_from_file_location("erp_compras_purchase_create_service", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.ErpComprasPurchaseCreateService().ejecutar(context)
