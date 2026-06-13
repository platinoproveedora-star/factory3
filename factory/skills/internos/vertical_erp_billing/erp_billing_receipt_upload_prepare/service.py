from __future__ import annotations

import json
import os
import re
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import blank, resolve_billing_context  # noqa: E402


ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9._-]+")


class ErpBillingReceiptUploadPrepareService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        bucket = blank(
            context.get("receipt_file_bucket")
            or context.get("document_file_bucket")
            or context.get("bucket")
            or os.getenv("BILLING_RECEIPTS_BUCKET")
        )
        if not bucket:
            return {"ok": False, "error": "receipt_file_bucket/bucket requerido en context o BILLING_RECEIPTS_BUCKET"}

        content_type = str(context.get("content_type") or "").strip().lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            return {"ok": False, "error": "content_type debe ser PDF, JPEG, PNG o WEBP"}

        size_bytes = int(context.get("size_bytes") or context.get("file_size") or 0)
        max_bytes = int(context.get("max_bytes") or DEFAULT_MAX_BYTES)
        if size_bytes <= 0:
            return {"ok": False, "error": "size_bytes requerido"}
        if size_bytes > max_bytes:
            return {"ok": False, "error": f"archivo excede max_bytes={max_bytes}"}

        path = blank(context.get("path") or context.get("receipt_file_path"))
        if not path:
            path = self._build_path(ctx, context, content_type)
        if ".." in path or path.startswith("/") or "\\" in path:
            return {"ok": False, "error": "path invalido"}

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se firmo URL de upload",
                "data": {
                    "bucket": bucket,
                    "path": path,
                    "content_type": content_type,
                    "upload_method": "PUT",
                    "signed_url": "https://example.invalid/signed-upload",
                    "expires_in_hint": "supabase_default",
                },
            }

        supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not supabase_url or not service_key:
            return {"ok": False, "error": "SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no configurados"}

        endpoint = f"{supabase_url}/storage/v1/object/upload/sign/{urllib.parse.quote(bucket)}/{urllib.parse.quote(path, safe='/')}"
        req = urllib.request.Request(
            endpoint,
            data=b"{}",
            method="POST",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Storage signed upload HTTP {exc.code}: {detail}"}
        except Exception as exc:
            return {"ok": False, "error": f"Storage signed upload: {exc}"}

        token = payload.get("token")
        signed_url = payload.get("signedURL") or payload.get("signedUrl") or payload.get("url")
        if not signed_url and token:
            signed_url = f"{endpoint}?token={urllib.parse.quote(str(token))}"
        if signed_url and signed_url.startswith("/"):
            signed_url = f"{supabase_url}/storage/v1{signed_url}"
        if not signed_url:
            return {"ok": False, "error": "Supabase no devolvio signed_url/token"}

        return {
            "ok": True,
            "data": {
                "bucket": bucket,
                "path": path,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "upload_method": "PUT",
                "signed_url": signed_url,
                "token": token,
                "expires_in_hint": "supabase_default",
            },
        }

    def _build_path(self, ctx: dict, context: dict, content_type: str) -> str:
        now = datetime.now(timezone.utc)
        ext = ALLOWED_CONTENT_TYPES[content_type]
        raw_name = blank(context.get("filename") or context.get("file_name")) or f"receipt{ext}"
        stem = Path(raw_name).stem[:60] or "receipt"
        safe_stem = SAFE_SEGMENT.sub("-", stem).strip("-_.") or "receipt"
        company_id = self._safe(ctx.get("company_id"))
        project_code = self._safe(ctx.get("project_code"))
        module_code = self._safe(ctx.get("module_code"))
        return "/".join(
            [
                company_id,
                project_code,
                module_code,
                "payments",
                f"{now:%Y}",
                f"{now:%m}",
                f"{uuid.uuid4().hex}-{safe_stem}{ext}",
            ]
        )

    def _safe(self, value: object) -> str:
        text = str(value or "").strip()
        return SAFE_SEGMENT.sub("-", text).strip("-_.") or "unknown"
