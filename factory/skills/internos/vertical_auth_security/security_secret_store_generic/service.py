"""Cifra un payload arbitrario con DEK/AES-256-GCM + KEK maestra. Guarda en
platform.secrets. Variante generica de security_secret_store — misma tabla y
mismo esquema de cifrado, sin forzar el shape cer_b64/key_b64/password (esa
sigue siendo la especifica para e.firma con validacion DER)."""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request


_KEK_VERSION = 1


class SecuritySecretStoreGenericService:

    def ejecutar(self, context: dict) -> dict:
        modulo_code    = (context.get("modulo_code") or "").strip()
        owner_user_id  = (context.get("owner_user_id") or context.get("user_id") or "").strip()
        scope_ref_id   = (context.get("scope_ref_id") or "").strip()
        scope_type     = (context.get("scope_type") or "").strip()
        payload        = context.get("payload") if isinstance(context.get("payload"), dict) else None

        kek_hex = (context.get("platform_kek_v1") or os.getenv("PLATFORM_KEK_V1", "")).strip()
        url = (context.get("platform_supabase_url") or os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))

        if not modulo_code:
            return {"ok": False, "error": "modulo_code requerido"}
        if not owner_user_id:
            return {"ok": False, "error": "owner_user_id requerido"}
        if not scope_type:
            return {"ok": False, "error": "scope_type requerido"}
        if not payload:
            return {"ok": False, "error": "payload (dict) requerido"}
        if not kek_hex:
            return {"ok": False, "error": "PLATFORM_KEK_V1 requerido"}
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — secreto no guardado", "data": {"modulo_code": modulo_code, "scope_type": scope_type}}

        try:
            encrypted = self._encrypt_payload(payload, kek_hex)
        except Exception:
            return {"ok": False, "error": "Error cifrando secreto"}

        row = {
            "modulo_code":     modulo_code,
            "owner_user_id":   owner_user_id,
            "scope_type":      scope_type,
            "scope_ref_id":    scope_ref_id or None,
            "dek_encrypted":   encrypted["dek_encrypted"],
            "nonce_dek":       encrypted["nonce_dek"],
            "kek_version":     _KEK_VERSION,
            "payload_cifrado": encrypted["payload_cifrado"],
        }

        try:
            self._pg_delete_existing(url, key, owner_user_id, scope_type, scope_ref_id)
            rows = self._pg_insert(url, key, row)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase {e.code}: {body[:200]}"}
        except Exception:
            return {"ok": False, "error": "Error guardando secreto cifrado"}

        secret_id = rows[0].get("id") if rows else None
        return {"ok": True, "message": f"secreto cifrado y guardado (scope={scope_type})", "data": {"secret_id": secret_id, "modulo_code": modulo_code, "kek_version": _KEK_VERSION}}

    def _encrypt_payload(self, payload: dict, kek_hex: str) -> dict:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets as _sec

        kek = bytes.fromhex(kek_hex)
        dek = _sec.token_bytes(32)

        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        nonce_payload = _sec.token_bytes(12)
        payload_ct = AESGCM(dek).encrypt(nonce_payload, payload_bytes, None)

        nonce_dek = _sec.token_bytes(12)
        dek_ct = AESGCM(kek).encrypt(nonce_dek, dek, None)

        return {
            "dek_encrypted": base64.b64encode(dek_ct).decode(),
            "nonce_dek": base64.b64encode(nonce_dek).decode(),
            "payload_cifrado": {
                "ciphertext": base64.b64encode(payload_ct).decode(),
                "nonce": base64.b64encode(nonce_payload).decode(),
            },
        }

    def _pg_delete_existing(self, url: str, key: str, owner_user_id: str, scope_type: str, scope_ref_id: str) -> None:
        import urllib.parse

        qs = f"owner_user_id=eq.{urllib.parse.quote(owner_user_id)}&scope_type=eq.{urllib.parse.quote(scope_type)}"
        if scope_ref_id:
            qs += f"&scope_ref_id=eq.{urllib.parse.quote(scope_ref_id)}"
        req = urllib.request.Request(
            f"{url}/rest/v1/secrets?{qs}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Profile": "platform",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="DELETE",
        )
        try:
            urllib.request.urlopen(req, timeout=15).read()
        except urllib.error.HTTPError:
            pass

    def _pg_insert(self, url: str, key: str, row: dict) -> list:
        req = urllib.request.Request(
            f"{url}/rest/v1/secrets",
            data=json.dumps(row).encode("utf-8"),
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Content-Profile": "platform",
                "Prefer": "return=representation",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
