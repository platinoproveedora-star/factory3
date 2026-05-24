from __future__ import annotations
import base64, os, urllib.request, urllib.error


class StorageUploadService:
    def ejecutar(self, context: dict) -> dict:
        bucket       = context.get("bucket", "")
        path         = context.get("path", "")
        content_b64  = context.get("content_b64", "")
        content_type = context.get("content_type", "application/octet-stream")

        if not bucket or not path or not content_b64:
            return {"ok": False, "error": "bucket, path y content_b64 son requeridos"}

        try:
            file_bytes = base64.b64decode(content_b64)
        except Exception as e:
            return {"ok": False, "error": f"Error decodificando base64: {e}"}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no configurados"}

        req = urllib.request.Request(
            f"{url}/storage/v1/object/{bucket}/{path}",
            data=file_bytes, method="POST",
            headers={
                "apikey":        key,
                "Authorization": f"Bearer {key}",
                "Content-Type":  content_type,
                "x-upsert":      "true",
                "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                r.read()
            public_url = f"{url}/storage/v1/object/public/{bucket}/{path}"
            return {"ok": True, "data": {"url": public_url, "path": path, "bucket": bucket}}
        except urllib.error.HTTPError as e:
            return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode()}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
