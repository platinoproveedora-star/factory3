from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import blank, resolve_billing_context  # noqa: E402


class ErpBillingReceiptLinkCreateService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result

        bucket = blank(context.get("receipt_file_bucket") or context.get("bucket"))
        path = blank(context.get("receipt_file_path") or context.get("path"))
        if not bucket or not path:
            return {"ok": False, "error": "receipt_file_bucket y receipt_file_path requeridos"}
        if ".." in path or path.startswith("/") or "\\" in path:
            return {"ok": False, "error": "receipt_file_path invalido"}
        expires_in = min(max(int(context.get("expires_in") or 600), 60), 3600)

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se firmo comprobante", "data": {"url": "https://example.invalid/receipt", "expires_in": expires_in}}

        supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not supabase_url or not service_key:
            return {"ok": False, "error": "SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no configurados"}

        object_path = f"{urllib.parse.quote(bucket)}/{urllib.parse.quote(path, safe='/')}"
        endpoint = f"{supabase_url}/storage/v1/object/sign/{object_path}"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps({"expiresIn": expires_in}).encode("utf-8"),
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
            return {"ok": False, "error": f"Storage signed link HTTP {exc.code}: {detail}"}
        except Exception as exc:
            return {"ok": False, "error": f"Storage signed link: {exc}"}

        signed_url = payload.get("signedURL") or payload.get("signedUrl") or payload.get("url")
        if signed_url and signed_url.startswith("/"):
            signed_url = f"{supabase_url}/storage/v1{signed_url}"
        if not signed_url:
            return {"ok": False, "error": "Supabase no devolvio URL firmada"}
        return {"ok": True, "data": {"url": signed_url, "expires_in": expires_in, "bucket": bucket, "path": path}}
