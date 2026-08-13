"""Descifra un payload arbitrario desde platform.secrets. SOLO server-to-server."""
from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request


class SecuritySecretRetrieveGenericService:

    def ejecutar(self, context: dict) -> dict:
        scope_ref_id = (context.get("scope_ref_id") or "").strip()
        scope_type   = (context.get("scope_type") or "").strip()

        kek_hex = (context.get("platform_kek_v1") or os.getenv("PLATFORM_KEK_V1", "")).strip()
        url = (context.get("platform_supabase_url") or os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))

        if not scope_type:
            return {"ok": False, "error": "scope_type requerido"}
        if not kek_hex:
            return {"ok": False, "error": "PLATFORM_KEK_V1 requerido"}
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"payload": {}}}

        qs = f"?scope_type=eq.{urllib.parse.quote(scope_type)}"
        if scope_ref_id:
            qs += f"&scope_ref_id=eq.{urllib.parse.quote(scope_ref_id)}"
        qs += "&select=dek_encrypted,nonce_dek,kek_version,payload_cifrado&order=id.desc&limit=1"
        req = urllib.request.Request(
            f"{url}/rest/v1/secrets{qs}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Accept-Profile": "platform",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                rows = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "error": "Error consultando vault"}

        if not rows:
            return {"ok": False, "error": f"No se encontro secreto para scope_type={scope_type}"}

        try:
            payload = self._decrypt_payload(rows[0], kek_hex)
        except Exception:
            return {"ok": False, "error": "Error descifrando secreto — KEK incorrecta o datos corruptos"}

        return {"ok": True, "message": "Secreto descifrado", "data": {"payload": payload}}

    def _decrypt_payload(self, row: dict, kek_hex: str) -> dict:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        kek = bytes.fromhex(kek_hex)
        dek_ct = base64.b64decode(row["dek_encrypted"])
        nonce_dek = base64.b64decode(row["nonce_dek"])
        dek = AESGCM(kek).decrypt(nonce_dek, dek_ct, None)

        cifrado = row["payload_cifrado"]
        payload_ct = base64.b64decode(cifrado["ciphertext"])
        nonce_payload = base64.b64decode(cifrado["nonce"])
        payload_bytes = AESGCM(dek).decrypt(nonce_payload, payload_ct, None)

        return json.loads(payload_bytes.decode("utf-8"))
