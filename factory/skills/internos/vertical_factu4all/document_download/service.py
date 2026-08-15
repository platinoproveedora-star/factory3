from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_EXPIRES_SECONDS = 300


class DocumentDownloadService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        file_type = str(context.get("file_type") or "xml").strip().lower()
        if not company_id or not folio:
            return {"ok": False, "error": "missing_fields", "data": {"missing": ["company_id", "folio"]}}
        if file_type not in ("xml", "pdf"):
            return {"ok": False, "error": "file_type debe ser xml|pdf"}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        doc_res = db.rest_select("cfdi_documents", filters={"company_id": f"eq.{company_id}", "folio": f"eq.{folio}"}, select="id", limit=1)
        if not doc_res.get("ok") or not doc_res.get("data"):
            return {"ok": False, "error": "cfdi_document_not_found"}
        cfdi_document_id = doc_res["data"][0]["id"]

        file_res = db.rest_select(
            "document_files",
            filters={"cfdi_document_id": f"eq.{cfdi_document_id}", "file_type": f"eq.{file_type}"},
            select="storage_bucket,storage_path",
            limit=1,
        )
        if not file_res.get("ok") or not file_res.get("data"):
            return {"ok": False, "error": "file_not_found", "data": {"detail": f"no hay {file_type} guardado para este CFDI"}}
        row = file_res["data"][0]

        signed = self._sign_url(row["storage_bucket"], row["storage_path"])
        if not signed:
            return {"ok": False, "error": "sign_url_failed"}
        return {"ok": True, "data": {"url": signed, "file_type": file_type}}

    def _sign_url(self, bucket: str, path: str) -> str:
        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return ""
        payload = json.dumps({"expiresIn": _EXPIRES_SECONDS}).encode("utf-8")
        req = urllib.request.Request(
            f"{url}/storage/v1/object/sign/{bucket}/{path}",
            data=payload,
            method="POST",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError:
            return ""
        except Exception:
            return ""
        signed_path = body.get("signedURL") or ""
        if not signed_path:
            return ""
        return f"{url}/storage/v1{signed_path}"
