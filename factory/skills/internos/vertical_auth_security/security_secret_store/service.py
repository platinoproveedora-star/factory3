"""Cifra e.firma con DEK/AES-256-GCM + KEK maestra. Guarda en platform.secrets. Sin logs de credenciales."""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request


_KEK_VERSION = 1


class SecuritySecretStoreService:

    def ejecutar(self, context: dict) -> dict:
        modulo_code    = (context.get("modulo_code") or "").strip()
        owner_user_id  = (context.get("owner_user_id") or context.get("user_id") or "").strip()
        managed_rfc_id = (context.get("managed_rfc_id") or "").strip()
        scope_type     = (context.get("scope_type") or "sat_efirma").strip()

        cer_b64  = (context.get("cer_b64") or "").strip()
        key_b64  = (context.get("key_b64") or "").strip()
        password = (context.get("key_password") or context.get("password") or "").strip()

        kek_hex = (context.get("platform_kek_v1") or
                   os.getenv("PLATFORM_KEK_V1", "")).strip()
        url = (context.get("platform_supabase_url") or
               os.getenv("PLATFORM_SUPABASE_URL", "")).rstrip("/")
        key = (context.get("platform_supabase_service_role_key") or
               os.getenv("PLATFORM_SUPABASE_SERVICE_ROLE_KEY", ""))

        if not modulo_code:
            return {"ok": False, "error": "modulo_code requerido"}
        if not owner_user_id:
            return {"ok": False, "error": "owner_user_id requerido"}
        if not all([cer_b64, key_b64, password]):
            return {"ok": False, "error": "cer_b64, key_b64 y key_password requeridos"}
        if not kek_hex:
            return {"ok": False, "error": "PLATFORM_KEK_V1 requerido"}
        if not url or not key:
            return {"ok": False, "error": "Faltan PLATFORM_SUPABASE_URL o PLATFORM_SUPABASE_SERVICE_ROLE_KEY"}

        # Validar que .cer y .key parsean como DER antes de cifrar
        try:
            self._validate_der(cer_b64, key_b64, password)
        except Exception:
            return {"ok": False, "error": "cer_b64 o key_b64 inválidos — no parsean como DER con ese password"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run — secreto no guardado", "data": {
                "modulo_code": modulo_code, "scope_type": scope_type,
            }}

        try:
            encrypted = self._encrypt_payload(
                {"cer_b64": cer_b64, "key_b64": key_b64, "password": password},
                kek_hex,
            )
        except Exception:
            return {"ok": False, "error": "Error cifrando secreto"}

        row = {
            "modulo_code":     modulo_code,
            "owner_user_id":   owner_user_id,
            "scope_type":      scope_type,
            "scope_ref_id":    managed_rfc_id or None,
            "dek_encrypted":   encrypted["dek_encrypted"],
            "nonce_dek":       encrypted["nonce_dek"],
            "kek_version":     _KEK_VERSION,
            "payload_cifrado": encrypted["payload_cifrado"],
        }

        try:
            rows = self._pg_post(url, key, row)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 409 or "duplicate" in body.lower():
                return {"ok": False, "error": "Ya existe un secreto para este RFC/scope"}
            return {"ok": False, "error": f"Supabase {e.code}: {body[:200]}"}
        except Exception:
            return {"ok": False, "error": "Error guardando secreto cifrado"}

        secret_id = rows[0].get("id") if rows else None
        return {
            "ok":      True,
            "message": f"e.firma cifrada y guardada (scope={scope_type})",
            "data":    {"secret_id": secret_id, "modulo_code": modulo_code, "kek_version": _KEK_VERSION},
        }

    def _validate_der(self, cer_b64: str, key_b64: str, password: str) -> None:
        from cryptography.hazmat.primitives import serialization
        cer_der = base64.b64decode(cer_b64)
        key_der = base64.b64decode(key_b64)
        serialization.load_der_private_key(key_der, password=password.encode())
        from cryptography import x509
        x509.load_der_x509_certificate(cer_der)

    def _encrypt_payload(self, payload: dict, kek_hex: str) -> dict:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets as _sec

        kek = bytes.fromhex(kek_hex)

        # DEK aleatoria 256-bit
        dek = _sec.token_bytes(32)

        # Cifrar payload con DEK
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        nonce_payload = _sec.token_bytes(12)
        payload_ct    = AESGCM(dek).encrypt(nonce_payload, payload_bytes, None)

        # Cifrar DEK con KEK
        nonce_dek  = _sec.token_bytes(12)
        dek_ct     = AESGCM(kek).encrypt(nonce_dek, dek, None)

        return {
            "dek_encrypted":   base64.b64encode(dek_ct).decode(),
            "nonce_dek":       base64.b64encode(nonce_dek).decode(),
            "payload_cifrado": {
                "ciphertext": base64.b64encode(payload_ct).decode(),
                "nonce":      base64.b64encode(nonce_payload).decode(),
            },
        }

    def _pg_post(self, url: str, key: str, row: dict) -> list:
        req = urllib.request.Request(
            f"{url}/rest/v1/secrets",
            data=json.dumps(row).encode("utf-8"),
            headers={
                "apikey":          key,
                "Authorization":   f"Bearer {key}",
                "Content-Type":    "application/json",
                "Content-Profile": "platform",
                "Prefer":          "return=representation",
                "User-Agent":      "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
