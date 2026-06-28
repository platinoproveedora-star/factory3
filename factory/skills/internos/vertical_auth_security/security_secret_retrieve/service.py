"""Descifra e.firma desde platform.secrets. SOLO server-to-server. Nunca exponer via HTTP."""
from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request


class SecuritySecretRetrieveService:

    def ejecutar(self, context: dict) -> dict:
        managed_rfc_id = (context.get("managed_rfc_id") or "").strip()
        scope_type     = (context.get("scope_type") or "sat_efirma").strip()

        kek_hex = (context.get("platform_kek_v1") or
                   os.getenv("PLATFORM_KEK_V1", "")).strip()
        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))

        if not managed_rfc_id:
            return {"ok": False, "error": "managed_rfc_id requerido"}
        if not kek_hex:
            return {"ok": False, "error": "PLATFORM_KEK_V1 requerido"}
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {
                "cer_b64": "DRY", "key_b64": "DRY", "password": "DRY",
            }}

        # Buscar secreto en DB
        qs = (f"?scope_ref_id=eq.{urllib.parse.quote(managed_rfc_id)}"
              f"&scope_type=eq.{urllib.parse.quote(scope_type)}"
              f"&select=dek_encrypted,nonce_dek,kek_version,payload_cifrado&limit=1")
        req = urllib.request.Request(
            f"{url}/rest/v1/secrets{qs}",
            headers={
                "apikey":         key,
                "Authorization":  f"Bearer {key}",
                "Accept-Profile": "platform",
                "User-Agent":     "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                rows = json.loads(resp.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "error": "Error consultando vault"}

        if not rows:
            return {"ok": False, "error": f"No se encontró secreto para managed_rfc_id={managed_rfc_id}"}

        row = rows[0]
        try:
            payload = self._decrypt_payload(row, kek_hex)
        except Exception:
            return {"ok": False, "error": "Error descifrando secreto — KEK incorrecta o datos corruptos"}

        return {
            "ok":      True,
            "message": "Secreto descifrado",
            "data": {
                "cer_b64":     payload.get("cer_b64", ""),
                "key_b64":     payload.get("key_b64", ""),
                "key_password": payload.get("password", ""),
            },
        }

    def _decrypt_payload(self, row: dict, kek_hex: str) -> dict:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        kek = bytes.fromhex(kek_hex)

        dek_ct    = base64.b64decode(row["dek_encrypted"])
        nonce_dek = base64.b64decode(row["nonce_dek"])
        dek       = AESGCM(kek).decrypt(nonce_dek, dek_ct, None)

        cifrado        = row["payload_cifrado"]
        payload_ct     = base64.b64decode(cifrado["ciphertext"])
        nonce_payload  = base64.b64decode(cifrado["nonce"])
        payload_bytes  = AESGCM(dek).decrypt(nonce_payload, payload_ct, None)

        return json.loads(payload_bytes.decode("utf-8"))
