from __future__ import annotations

import os

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_MOTIVOS_VALIDOS = {"01", "02", "03", "04"}


# ── ADAPTER PAC GENERICO (duplicado minimo de pac_stamp; carpeta exclusiva) ──

class PacAdapter:
    provider_name = "generic"

    def cancel(self, uuid_sat: str, motivo: str) -> dict:
        raise NotImplementedError


class NullPacAdapter(PacAdapter):
    provider_name = "sandbox_simulated"

    def cancel(self, uuid_sat: str, motivo: str) -> dict:
        return {"ok": True}


class SwSapienPacAdapter(PacAdapter):
    provider_name = "sw_sapien"

    def __init__(self, user: str, password: str, url: str):
        self.user, self.password, self.url = user, password, url

    def cancel(self, uuid_sat: str, motivo: str) -> dict:
        raise NotImplementedError("Conectar API real de SW Sapien — credenciales detectadas pero integracion pendiente")


class FacturamaPacAdapter(PacAdapter):
    provider_name = "facturama"

    def __init__(self, user: str, password: str, url: str):
        self.user, self.password, self.url = user, password, url

    def cancel(self, uuid_sat: str, motivo: str) -> dict:
        raise NotImplementedError("Conectar API real de Facturama — credenciales detectadas pero integracion pendiente")


_PROVIDERS = {"sw_sapien": SwSapienPacAdapter, "facturama": FacturamaPacAdapter}


def get_pac_adapter(context: dict) -> PacAdapter:
    provider = str(context.get("pac_provider") or os.getenv("PAC_PROVIDER") or "").strip().lower()
    user = context.get("pac_user") or os.getenv("PAC_USER")
    password = context.get("pac_password") or os.getenv("PAC_PASSWORD")
    url = context.get("pac_url") or os.getenv("PAC_URL")
    adapter_cls = _PROVIDERS.get(provider)
    if adapter_cls and user and password and url:
        return adapter_cls(user, password, url)
    return NullPacAdapter()


# ── SKILL ─────────────────────────────────────────────────────────────────────

class CartaporteCancelService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        stamp_folio = str(context.get("stamp_folio") or "").strip()
        motivo = str(context.get("motivo_sat") or "").strip()
        if not empresa_id or not stamp_folio:
            return {"ok": False, "error": "missing_fields", "data": {"missing": ["empresa_id", "stamp_folio"]}}
        if not context.get("confirm"):
            return {"ok": False, "error": "confirm_required"}
        if motivo not in _MOTIVOS_VALIDOS:
            return {"ok": False, "error": "invalid_cartaporte", "data": {"detail": "motivo_sat debe ser 01, 02, 03 o 04"}}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        stamp_res = db.rest_select("cartaporte_stamps", filters={"empresa_id": f"eq.{empresa_id}", "stamp_folio": f"eq.{stamp_folio}"}, select="*", limit=1)
        if not stamp_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": stamp_res.get("error")}}
        rows = stamp_res.get("data") or []
        if not rows:
            return {"ok": False, "error": "stamp_not_found"}
        current = rows[0]
        if current.get("stamp_status") != "stamped":
            return {"ok": False, "error": "invalid_cartaporte", "data": {"detail": "solo se puede cancelar un timbre con status=stamped"}}

        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run: no se cancelo ante el PAC", "data": {"cartaporte_stamp": current, "warnings": ["dry_run"]}}

        adapter = get_pac_adapter(context)
        try:
            cancel_result = adapter.cancel(current.get("uuid_sat"), motivo)
        except NotImplementedError as exc:
            cancel_result = {"ok": False, "error": str(exc)}

        if not cancel_result.get("ok"):
            return {"ok": False, "error": "pac_error", "data": {"detail": cancel_result.get("error")}}

        upd = db.rest_update("cartaporte_stamps", values={"stamp_status": "canceled"}, filters={"empresa_id": f"eq.{empresa_id}", "stamp_folio": f"eq.{stamp_folio}"})
        if not upd.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": upd.get("error")}}
        persisted = (upd.get("data") or [current])[0]

        warnings = []
        if adapter.provider_name == "sandbox_simulated":
            warnings.append("sandbox_simulated: cancelacion simulada, no es real ante el SAT")
        return {"ok": True, "data": {"cartaporte_stamp": persisted, "warnings": warnings}}
