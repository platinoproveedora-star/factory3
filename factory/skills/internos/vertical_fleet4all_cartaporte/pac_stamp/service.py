from __future__ import annotations

import os
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"
_OUT_DIR = Path("/tmp/fleet4all_cfdi")


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


# ── ADAPTER PAC GENERICO ──────────────────────────────────────────────────────
# Contrato comun: stamp(cartaporte)->{"ok","uuid_sat","xml","error"} y
# cancel(uuid_sat, motivo)->{"ok","error"}. Cambiar de proveedor = agregar una
# clase nueva aqui y registrarla en get_pac_adapter; pac_stamp/cartaporte_cancel
# no cambian.

class PacAdapter:
    provider_name = "generic"

    def stamp(self, cartaporte: dict) -> dict:
        raise NotImplementedError

    def cancel(self, uuid_sat: str, motivo: str) -> dict:
        raise NotImplementedError


class NullPacAdapter(PacAdapter):
    """Adapter simulado — se usa mientras no haya credenciales PAC reales.
    Genera un uuid_sat y xml de prueba deterministas para poder probar todo
    el flujo (build->validate->stamp) sin timbre real."""

    provider_name = "sandbox_simulated"

    def stamp(self, cartaporte: dict) -> dict:
        fake_uuid = str(_uuid.uuid4()).upper()
        xml = (
            f"<cfdi:Comprobante uuid=\"{fake_uuid}\" simulated=\"true\" "
            f"tipo=\"{cartaporte.get('cfdi_type')}\">"
            f"<Origen>{cartaporte.get('origin')}</Origen>"
            f"<Destino>{cartaporte.get('destination')}</Destino>"
            f"</cfdi:Comprobante>"
        )
        return {"ok": True, "uuid_sat": fake_uuid, "xml": xml}

    def cancel(self, uuid_sat: str, motivo: str) -> dict:
        return {"ok": True}


class SwSapienPacAdapter(PacAdapter):
    """Placeholder para SW Sapien. Implementar stamp/cancel contra su API real
    cuando existan credenciales (PAC_USER, PAC_PASSWORD, PAC_URL)."""

    provider_name = "sw_sapien"

    def __init__(self, user: str, password: str, url: str):
        self.user = user
        self.password = password
        self.url = url

    def stamp(self, cartaporte: dict) -> dict:
        raise NotImplementedError("Conectar API real de SW Sapien — credenciales detectadas pero integracion pendiente")

    def cancel(self, uuid_sat: str, motivo: str) -> dict:
        raise NotImplementedError("Conectar API real de SW Sapien — credenciales detectadas pero integracion pendiente")


class FacturamaPacAdapter(PacAdapter):
    """Placeholder para Facturama. Implementar stamp/cancel contra su API real
    cuando existan credenciales (PAC_USER, PAC_PASSWORD, PAC_URL)."""

    provider_name = "facturama"

    def __init__(self, user: str, password: str, url: str):
        self.user = user
        self.password = password
        self.url = url

    def stamp(self, cartaporte: dict) -> dict:
        raise NotImplementedError("Conectar API real de Facturama — credenciales detectadas pero integracion pendiente")

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

class PacStampService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        stamp_folio = str(context.get("stamp_folio") or "").strip()
        cartaporte = context.get("cartaporte") if isinstance(context.get("cartaporte"), dict) else None
        if not empresa_id or not stamp_folio or not cartaporte:
            return {"ok": False, "error": "missing_fields", "data": {"missing": ["empresa_id", "stamp_folio", "cartaporte"]}}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        stamp_res = db.rest_select("cartaporte_stamps", filters={"empresa_id": f"eq.{empresa_id}", "stamp_folio": f"eq.{stamp_folio}"}, select="*", limit=1)
        if not stamp_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": stamp_res.get("error")}}
        rows = stamp_res.get("data") or []
        if not rows:
            return {"ok": False, "error": "stamp_not_found"}
        current = rows[0]

        if current.get("stamp_status") == "stamped":
            return {"ok": True, "data": {"cartaporte_stamp": current, "warnings": ["already_stamped: se devolvio el timbre existente, no se re-timbro"]}}

        validate_res = _runner().run(
            "vertical_fleet4all_cartaporte/cartaporte_validate",
            {"cartaporte": cartaporte, "rfc": context.get("rfc")},
        )
        if not validate_res.get("ok"):
            return validate_res

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: solo validacion local, PAC no contactado",
                "data": {"cartaporte_stamp": current, "warnings": ["dry_run: PAC no contactado"]},
            }

        rfc = str(context.get("rfc") or "").strip().upper()
        if not rfc:
            return {"ok": False, "error": "credentials_not_found", "data": {"detail": "rfc requerido para localizar el CSD"}}
        csd_res = _runner().run(
            "vertical_fleet4all_cartaporte/csd_vault",
            {"action": "retrieve", "empresa_id": empresa_id, "rfc": rfc, "dry_run": False},
        )
        if not csd_res.get("ok"):
            return {"ok": False, "error": "credentials_not_found", "data": {"detail": csd_res.get("error")}}

        adapter = get_pac_adapter(context)
        try:
            stamp_result = adapter.stamp(cartaporte)
        except NotImplementedError as exc:
            stamp_result = {"ok": False, "error": str(exc)}

        if not stamp_result.get("ok"):
            db.rest_update(
                "cartaporte_stamps",
                values={"stamp_status": "error", "error_detail": stamp_result.get("error"), "pac_provider": adapter.provider_name},
                filters={"empresa_id": f"eq.{empresa_id}", "stamp_folio": f"eq.{stamp_folio}"},
            )
            return {"ok": False, "error": "pac_error", "data": {"detail": stamp_result.get("error")}}

        xml_path = self._write_xml(empresa_id, stamp_folio, stamp_result.get("xml") or "")
        upd = db.rest_update(
            "cartaporte_stamps",
            values={
                "uuid_sat": stamp_result.get("uuid_sat"),
                "xml_path": xml_path,
                "pac_provider": adapter.provider_name,
                "stamp_status": "stamped",
                "stamped_at": datetime.now(timezone.utc).isoformat(),
                "error_detail": None,
            },
            filters={"empresa_id": f"eq.{empresa_id}", "stamp_folio": f"eq.{stamp_folio}"},
        )
        if not upd.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": upd.get("error")}}
        persisted = (upd.get("data") or [current])[0]

        warnings = []
        if adapter.provider_name == "sandbox_simulated":
            warnings.append("sandbox_simulated: uuid_sat de prueba, no es un timbre fiscal real")

        return {"ok": True, "data": {"cartaporte_stamp": persisted, "warnings": warnings}}

    def _write_xml(self, empresa_id: str, stamp_folio: str, xml: str) -> str:
        _OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = _OUT_DIR / f"{empresa_id}_{stamp_folio}.xml"
        path.write_text(xml, encoding="utf-8")
        return str(path)
