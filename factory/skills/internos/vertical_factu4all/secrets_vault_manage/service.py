"""Vault propio de Factu4All — DEK/AES-256-GCM + KEK maestra (PLATFORM_KEK_V1),
guardado en factu4all.secrets_vault. No depende de platform.secrets (esa tiene
FK a un usuario especifico via owner_user_id, no sirve para secretos scoped a
company_id sin un usuario puntual)."""
from __future__ import annotations

import base64
import json
import os
import secrets as _sec

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"


class SecretsVaultManageService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        scope_type = str(context.get("scope_type") or "").strip()
        scope_ref = str(context.get("scope_ref") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}
        if not scope_type:
            return {"ok": False, "error": "scope_type_requerido"}

        action = str(context.get("action") or "status").strip().lower()
        if action == "store":
            return self._store(context, company_id, scope_type, scope_ref)
        if action == "retrieve":
            return {"ok": False, "error": "retrieve movido a vertical_factu4all/secrets_vault_retrieve (internal_only, no accesible via /run/)"}
        return self._status(company_id, scope_type, scope_ref)

    def _kek(self) -> bytes | None:
        kek_hex = os.getenv("PLATFORM_KEK_V1", "").strip()
        if not kek_hex:
            return None
        try:
            return bytes.fromhex(kek_hex)
        except ValueError:
            return None

    def _store(self, context: dict, company_id: str, scope_type: str, scope_ref: str) -> dict:
        payload = context.get("payload") if isinstance(context.get("payload"), dict) else None
        if not payload:
            return {"ok": False, "error": "payload_dict_requerido"}
        kek = self._kek()
        if not kek:
            return {"ok": False, "error": "PLATFORM_KEK_V1 requerido"}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: secreto no guardado", "data": {"company_id": company_id, "scope_type": scope_type, "scope_ref": scope_ref}}

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        dek = _sec.token_bytes(32)
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        nonce_payload = _sec.token_bytes(12)
        payload_ct = AESGCM(dek).encrypt(nonce_payload, payload_bytes, None)
        nonce_dek = _sec.token_bytes(12)
        dek_ct = AESGCM(kek).encrypt(nonce_dek, dek, None)

        row = {
            "company_id": company_id,
            "scope_type": scope_type,
            "scope_ref": scope_ref,
            "dek_encrypted": base64.b64encode(dek_ct).decode(),
            "nonce_dek": base64.b64encode(nonce_dek).decode(),
            "kek_version": 1,
            "payload_cifrado": {
                "ciphertext": base64.b64encode(payload_ct).decode(),
                "nonce": base64.b64encode(nonce_payload).decode(),
            },
        }

        db = SupabaseClient({"schema": _SCHEMA})
        res = db.rest_upsert("secrets_vault", row, "company_id,scope_type,scope_ref")
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "message": "secreto guardado", "data": {"company_id": company_id, "scope_type": scope_type, "scope_ref": scope_ref}}

    def _status(self, company_id: str, scope_type: str, scope_ref: str) -> dict:
        db = SupabaseClient({"schema": _SCHEMA})
        filters = {"company_id": f"eq.{company_id}", "scope_type": f"eq.{scope_type}", "scope_ref": f"eq.{scope_ref}"}
        res = db.rest_select("secrets_vault", filters=filters, select="id,updated_at", limit=1)
        configured = bool(res.get("ok") and res.get("data"))
        return {"ok": True, "data": {"company_id": company_id, "scope_type": scope_type, "scope_ref": scope_ref, "configured": configured}}
