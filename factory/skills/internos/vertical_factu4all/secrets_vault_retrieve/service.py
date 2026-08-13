"""Descifra secretos de factu4all.secrets_vault. SOLO server-to-server —
este skill esta marcado internal_only en su manifest.json, factory_api.py lo
bloquea en /run/ HTTP. Unico consumidor esperado: pac_stamp via SkillRunner."""
from __future__ import annotations

import base64
import json
import os

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"


class SecretsVaultRetrieveService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        scope_type = str(context.get("scope_type") or "").strip()
        scope_ref = str(context.get("scope_ref") or "").strip()
        if not company_id or not scope_type:
            return {"ok": False, "error": "company_id_y_scope_type_requeridos"}

        kek_hex = os.getenv("PLATFORM_KEK_V1", "").strip()
        if not kek_hex:
            return {"ok": False, "error": "PLATFORM_KEK_V1 requerido"}
        try:
            kek = bytes.fromhex(kek_hex)
        except ValueError:
            return {"ok": False, "error": "PLATFORM_KEK_V1 invalido"}

        db = SupabaseClient({"schema": _SCHEMA})
        filters = {"company_id": f"eq.{company_id}", "scope_type": f"eq.{scope_type}", "scope_ref": f"eq.{scope_ref}"}
        res = db.rest_select("secrets_vault", filters=filters, select="dek_encrypted,nonce_dek,kek_version,payload_cifrado", limit=1)
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        rows = res.get("data") or []
        if not rows:
            return {"ok": False, "error": "secret_not_found"}

        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            row = rows[0]
            dek_ct = base64.b64decode(row["dek_encrypted"])
            nonce_dek = base64.b64decode(row["nonce_dek"])
            dek = AESGCM(kek).decrypt(nonce_dek, dek_ct, None)
            cifrado = row["payload_cifrado"]
            payload_ct = base64.b64decode(cifrado["ciphertext"])
            nonce_payload = base64.b64decode(cifrado["nonce"])
            payload_bytes = AESGCM(dek).decrypt(nonce_payload, payload_ct, None)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return {"ok": False, "error": "decrypt_failed"}

        return {"ok": True, "data": {"payload": payload}}
