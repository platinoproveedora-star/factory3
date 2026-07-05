from __future__ import annotations

from pathlib import Path

_SCOPE_TYPE = "fleet4all_csd"
_MODULO_CODE = "fleet4all"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


def _managed_id(empresa_id: str, rfc: str) -> str:
    return f"fleet4all:{empresa_id}:{rfc}"


class CsdVaultService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        rfc = str(context.get("rfc") or "").strip().upper()
        if not empresa_id or not rfc:
            return {"ok": False, "error": "missing_required_fields"}

        action = str(context.get("action") or "status").strip().lower()
        if action == "store":
            return self._store(context, empresa_id, rfc)
        if action == "retrieve":
            return self._retrieve(context, empresa_id, rfc)
        return self._status(context, empresa_id, rfc)

    def _store(self, context: dict, empresa_id: str, rfc: str) -> dict:
        cer_b64 = str(context.get("cer_b64") or "").strip()
        key_b64 = str(context.get("key_b64") or "").strip()
        key_password = str(context.get("key_password") or "").strip()
        if not cer_b64 or not key_b64 or not key_password:
            return {"ok": False, "error": "missing_required_fields"}

        result = _runner().run(
            "vertical_auth_security/security_secret_store",
            {
                "modulo_code": _MODULO_CODE,
                "owner_user_id": empresa_id,
                "managed_rfc_id": _managed_id(empresa_id, rfc),
                "scope_type": _SCOPE_TYPE,
                "cer_b64": cer_b64,
                "key_b64": key_b64,
                "key_password": key_password,
                "dry_run": context.get("dry_run", True),
            },
        )
        if not result.get("ok"):
            return {"ok": False, "error": "credentials_not_found", "data": {"detail": result.get("error")}}

        return {
            "ok": True,
            "data": {
                "empresa_id": empresa_id,
                "rfc": rfc,
                "valid_until": context.get("valid_until"),
                "status": "would_store" if context.get("dry_run", True) else "active",
            },
        }

    def _retrieve(self, context: dict, empresa_id: str, rfc: str) -> dict:
        # Uso interno de pac_stamp unicamente. No exponer via bot/API publica.
        result = _runner().run(
            "vertical_auth_security/security_secret_retrieve",
            {"managed_rfc_id": _managed_id(empresa_id, rfc), "scope_type": _SCOPE_TYPE, "dry_run": context.get("dry_run", False)},
        )
        if not result.get("ok"):
            return {"ok": False, "error": "credentials_not_found", "data": {"detail": result.get("error")}}
        data = result.get("data") or {}
        return {
            "ok": True,
            "data": {"cer_b64": data.get("cer_b64", ""), "key_b64": data.get("key_b64", ""), "key_password": data.get("key_password", "")},
        }

    def _status(self, context: dict, empresa_id: str, rfc: str) -> dict:
        result = _runner().run(
            "vertical_auth_security/security_secret_retrieve",
            {"managed_rfc_id": _managed_id(empresa_id, rfc), "scope_type": _SCOPE_TYPE, "dry_run": False},
        )
        configured = bool(result.get("ok"))
        return {"ok": True, "data": {"empresa_id": empresa_id, "rfc": rfc, "configured": configured}}
