from __future__ import annotations

import base64
import os
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_BUCKET = "factu4all-documents"


# ── ADAPTER PAC ────────────────────────────────────────────────────────────
# Contrato: stamp/cancel/get_cfdi/download_xml/download_pdf. Copia
# independiente del patron usado en vertical_fleet4all_cartaporte/pac_stamp —
# mismo contrato, cero dependencia cruzada entre Fleet4All y Factu4All
# (son productos distintos). Cambiar de PAC = agregar una clase aqui y
# registrarla en get_pac_adapter; el resto del skill no cambia.

class PacAdapter:
    provider_name = "generic"

    def stamp(self, cfdi_draft: dict) -> dict:
        raise NotImplementedError

    def cancel(self, uuid_sat: str, motivo: str, related_cfdi_uuid: str | None = None) -> dict:
        raise NotImplementedError

    def get_cfdi(self, uuid_sat: str) -> dict:
        raise NotImplementedError

    def download_xml(self, uuid_sat: str) -> dict:
        raise NotImplementedError

    def download_pdf(self, uuid_sat: str) -> dict:
        raise NotImplementedError


class NullPacAdapter(PacAdapter):
    """Adapter simulado — sin credenciales PAC reales. Genera uuid/xml de
    prueba deterministas para poder correr todo el flujo (build->preview->
    stamp) sin timbre fiscal real."""

    provider_name = "sandbox_simulated"

    def stamp(self, cfdi_draft: dict) -> dict:
        fake_uuid = str(_uuid.uuid4()).upper()
        xml = (
            f"<cfdi:Comprobante uuid=\"{fake_uuid}\" simulated=\"true\" "
            f"tipo=\"{cfdi_draft.get('cfdi_type')}\">"
            f"<Emisor rfc=\"{cfdi_draft.get('issuer_rfc')}\"/>"
            f"<Receptor rfc=\"{cfdi_draft.get('party_rfc')}\"/>"
            f"<Total>{cfdi_draft.get('total')}</Total>"
            f"</cfdi:Comprobante>"
        )
        return {"ok": True, "uuid_sat": fake_uuid, "xml": xml}

    def cancel(self, uuid_sat: str, motivo: str, related_cfdi_uuid: str | None = None) -> dict:
        return {"ok": True}

    def get_cfdi(self, uuid_sat: str) -> dict:
        return {"ok": True, "data": {"uuid": uuid_sat, "status": "simulated"}}

    def download_xml(self, uuid_sat: str) -> dict:
        return {"ok": True, "data": {"xml": f"<cfdi:Comprobante uuid=\"{uuid_sat}\" simulated=\"true\"/>"}}

    def download_pdf(self, uuid_sat: str) -> dict:
        return {"ok": False, "error": "sandbox_simulated: sin PDF real"}


_CFDI_TYPE_SAT = {"ingreso": "I", "egreso": "E"}


class FacturamaPacAdapter(PacAdapter):
    """Facturama Multiemisor real. Payload armado segun el esquema CFDI 4.0
    documentado publicamente por Facturama (Issuer/Receiver/Items con
    Taxes[]). NO probado contra sandbox real todavia — validar nombres de
    campo exactos en cuanto haya credenciales Multiemisor Sandbox reales;
    Facturama puede ajustar shapes entre versiones de su API Lite."""

    provider_name = "facturama"

    def __init__(self, user: str, password: str, url: str):
        self.user = user
        self.password = password
        self.url = url.rstrip("/")

    def _auth_header(self) -> str:
        token = base64.b64encode(f"{self.user}:{self.password}".encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        import json as _json
        import urllib.error
        import urllib.request

        data = _json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            f"{self.url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": self._auth_header(),
                "Content-Type": "application/json",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return {"ok": True, "data": _json.loads(body) if body else {}}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Facturama HTTP {exc.code}: {detail[:500]}"}
        except Exception as exc:
            return {"ok": False, "error": f"Facturama request failed: {exc}"}

    def _build_payload(self, cfdi_draft: dict) -> dict:
        issuer = cfdi_draft.get("issuer") or {}
        party = cfdi_draft.get("party") or {}
        items = cfdi_draft.get("items") or []
        cfdi_type = _CFDI_TYPE_SAT.get(str(cfdi_draft.get("cfdi_type") or "ingreso"), "I")

        line_items = []
        for item in items:
            quantity = float(item.get("quantity") or 0)
            unit_price = float(item.get("unit_price") or 0)
            discount = float(item.get("discount_amount") or 0)
            subtotal = round(quantity * unit_price - discount, 2)
            tax_amount = float(item.get("tax_amount") or 0)
            line_items.append({
                "ProductCode": item.get("sat_product_key_snapshot"),
                "IdentificationNumber": item.get("source_product_key") or "",
                "Description": item.get("fiscal_product_name_snapshot") or "",
                "Unit": item.get("sat_unit_key_snapshot"),
                "UnitCode": item.get("sat_unit_key_snapshot"),
                "UnitPrice": unit_price,
                "Quantity": quantity,
                "Subtotal": subtotal,
                "Discount": discount,
                "TaxObject": item.get("tax_object_snapshot"),
                "Taxes": [
                    {"Total": tax_amount, "Name": "IVA", "Base": subtotal, "Rate": 0.16, "IsRetention": False}
                ] if tax_amount else [],
                "Total": round(subtotal + tax_amount, 2),
            })

        payload = {
            "Serie": cfdi_draft.get("series"),
            "Folio": str(cfdi_draft.get("cfdi_number") or ""),
            "Currency": cfdi_draft.get("currency") or "MXN",
            "ExpeditionPlace": issuer.get("expedition_place"),
            "PaymentForm": cfdi_draft.get("payment_form"),
            "PaymentMethod": cfdi_draft.get("payment_method"),
            "CfdiType": cfdi_type,
            "Exportation": "01",
            "Issuer": {
                "Rfc": issuer.get("rfc"),
                "Name": issuer.get("legal_name"),
                "FiscalRegime": issuer.get("fiscal_regime"),
            },
            "Receiver": {
                "Rfc": party.get("rfc"),
                "Name": party.get("legal_name"),
                "CfdiUse": cfdi_draft.get("uso_cfdi") or party.get("cfdi_use_default"),
                "FiscalRegime": party.get("tax_regime"),
                "TaxZipCode": party.get("tax_zip_code"),
            },
            "Items": line_items,
        }
        related_cfdi_uuid = cfdi_draft.get("related_cfdi_uuid")
        if related_cfdi_uuid:
            # NO probado contra sandbox real: nombre/forma exacta de este nodo
            # documentado por Facturama como "CfdiRelationships" — validar en
            # cuanto haya credenciales reales.
            payload["CfdiRelationships"] = [{
                "Type": cfdi_draft.get("related_cfdi_relation_type") or "04",
                "CfdiRelated": [{"Uuid": related_cfdi_uuid}],
            }]
        return payload

    def stamp(self, cfdi_draft: dict) -> dict:
        payload = self._build_payload(cfdi_draft)
        res = self._request("POST", "/api-lite/4/cfdis", payload)
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error")}
        body = res.get("data") or {}
        uuid_sat = (
            body.get("Uuid")
            or body.get("uuid")
            or (body.get("Complement") or {}).get("TaxStamp", {}).get("Uuid")
        )
        if not uuid_sat:
            return {"ok": False, "error": f"Facturama respondio sin UUID reconocible: {body}"}
        xml = body.get("Xml") or body.get("xml") or ""
        return {"ok": True, "uuid_sat": uuid_sat, "xml": xml, "raw": body}

    def cancel(self, uuid_sat: str, motivo: str, related_cfdi_uuid: str | None = None) -> dict:
        # NO probado contra sandbox real: nombre de query param para el folio
        # sustituto (motivo 01) documentado por Facturama como "uuidReplacement" —
        # validar en cuanto haya credenciales reales.
        path = f"/api-lite/cfdis/{uuid_sat}?motive={motivo}"
        if motivo == "01" and related_cfdi_uuid:
            path += f"&uuidReplacement={related_cfdi_uuid}"
        res = self._request("DELETE", path)
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error")}
        return {"ok": True}

    def get_cfdi(self, uuid_sat: str) -> dict:
        res = self._request("GET", f"/api-lite/cfdis/{uuid_sat}")
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error")}
        return {"ok": True, "data": res.get("data")}

    def _download(self, uuid_sat: str, fmt: str) -> dict:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(
            f"{self.url}/api/Cfdi/{fmt}/issuedLite/{uuid_sat}",
            headers={"Authorization": self._auth_header(), "User-Agent": "FactoryFactory/0.1 (+https://github.com/)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return {"ok": True, "bytes": resp.read()}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": f"Facturama HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def download_xml(self, uuid_sat: str) -> dict:
        res = self._download(uuid_sat, "xml")
        if not res.get("ok"):
            return res
        return {"ok": True, "data": {"xml": res["bytes"].decode("utf-8", errors="replace")}}

    def download_pdf(self, uuid_sat: str) -> dict:
        res = self._download(uuid_sat, "pdf")
        if not res.get("ok"):
            return res
        return {"ok": True, "data": {"pdf_b64": base64.b64encode(res["bytes"]).decode("ascii")}}


_PROVIDERS = {"facturama": FacturamaPacAdapter}


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


def _vault_credentials(company_id: str, provider: str) -> dict:
    """Busca user/password/url en secrets_vault_manage (scope_type=pac_credentials,
    scope_ref=provider). Nunca lanza — si no hay nada guardado, regresa {}."""
    if not company_id or not provider:
        return {}
    res = _runner().run(
        "vertical_factu4all/secrets_vault_retrieve",
        {"company_id": company_id, "scope_type": "pac_credentials", "scope_ref": provider},
    )
    if not res.get("ok"):
        return {}
    return (res.get("data") or {}).get("payload") or {}


def get_pac_adapter(context: dict, company_id: str = "") -> PacAdapter | None:
    """Regresa el adapter real si hay credenciales completas. Si no las hay,
    solo regresa NullPacAdapter (simulado) cuando el caller pide
    context.allow_simulated=true explicito — nunca por default, para que un
    timbrado real nunca se degrade en silencio a uno simulado por falta de
    credenciales."""
    provider = str(context.get("pac_provider") or os.getenv("FACTU4ALL_PAC_PROVIDER") or "").strip().lower()
    user = context.get("pac_user") or os.getenv("FACTU4ALL_PAC_USER")
    password = context.get("pac_password") or os.getenv("FACTU4ALL_PAC_PASSWORD")
    url = context.get("pac_url") or os.getenv("FACTU4ALL_PAC_URL")

    if provider and not (user and password and url):
        vault = _vault_credentials(company_id, provider)
        user = user or vault.get("user")
        password = password or vault.get("password")
        url = url or vault.get("url")

    adapter_cls = _PROVIDERS.get(provider)
    if adapter_cls and user and password and url:
        return adapter_cls(user, password, url)
    if context.get("allow_simulated"):
        return NullPacAdapter()
    return None


# ── SKILL ─────────────────────────────────────────────────────────────────

class PacStampService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        folio = str(context.get("folio") or "").strip()
        if not company_id or not folio:
            return {"ok": False, "error": "missing_fields", "data": {"missing": ["company_id", "folio"]}}

        db = SupabaseClient({**context, "schema": _SCHEMA})
        doc_res = db.rest_select("cfdi_documents", filters={"company_id": f"eq.{company_id}", "folio": f"eq.{folio}"}, select="*", limit=1)
        if not doc_res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": doc_res.get("error")}}
        rows = doc_res.get("data") or []
        if not rows:
            return {"ok": False, "error": "cfdi_document_not_found"}
        current = rows[0]

        action = str(context.get("action") or "stamp").strip().lower()
        if action == "cancel":
            return self._cancel(db, context, company_id, folio, current)
        if action == "status":
            return self._check_status(context, company_id, current)

        if current.get("status") in ("stamped", "simulated"):
            return {"ok": True, "data": {"cfdi_document": current, "warnings": [f"already_{current.get('status')}: se devolvio el CFDI existente, no se re-timbro"]}}

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: PAC no contactado",
                "data": {"cfdi_document": current, "warnings": ["dry_run: PAC no contactado"]},
            }

        issuer, party, items, missing = self._fetch_stamp_context(db, current)
        if missing:
            return {"ok": False, "error": "validation_failed", "data": {"missing": missing}}

        cfdi_draft = {
            **current,
            "issuer": issuer,
            "party": party,
            "items": items,
            "cfdi_number": self._folio_number(current.get("cfdi_folio"), current.get("series")),
            "issuer_rfc": issuer.get("rfc"),
            "party_rfc": party.get("rfc"),
        }

        adapter_context = {**context}
        adapter_context.setdefault("pac_provider", current.get("pac_provider"))
        adapter = get_pac_adapter(adapter_context, company_id)
        if adapter is None:
            db.rest_update(
                "cfdi_documents",
                values={"status": "stamp_error", "pac_error": "pac_not_configured"},
                filters={"company_id": f"eq.{company_id}", "folio": f"eq.{folio}"},
            )
            return {
                "ok": False,
                "error": "pac_not_configured",
                "data": {"detail": "No hay credenciales PAC configuradas para esta empresa. Configura Facturama en Empresa/Configuracion, o pasa allow_simulated=true explicito para probar con el sandbox simulado."},
            }
        try:
            stamp_result = adapter.stamp(cfdi_draft)
        except NotImplementedError as exc:
            stamp_result = {"ok": False, "error": str(exc)}

        if not stamp_result.get("ok"):
            db.rest_update(
                "cfdi_documents",
                values={"status": "stamp_error", "pac_error": stamp_result.get("error"), "pac_provider": adapter.provider_name},
                filters={"company_id": f"eq.{company_id}", "folio": f"eq.{folio}"},
            )
            return {"ok": False, "error": "pac_error", "data": {"detail": stamp_result.get("error")}}

        is_simulated = adapter.provider_name == "sandbox_simulated"
        final_status = "simulated" if is_simulated else "stamped"
        uuid_sat = stamp_result.get("uuid_sat") or ""
        storage_path = self._store_xml(company_id, current, uuid_sat or folio, stamp_result.get("xml") or "")

        upd = db.rest_update(
            "cfdi_documents",
            values={
                "uuid": uuid_sat,
                "xml_storage_path": storage_path,
                "pac_provider": adapter.provider_name,
                "status": final_status,
                "issued_at": datetime.now(timezone.utc).isoformat(),
                "pac_error": None,
            },
            filters={"company_id": f"eq.{company_id}", "folio": f"eq.{folio}"},
        )
        if not upd.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": upd.get("error")}}
        persisted = (upd.get("data") or [current])[0]

        self._apply_stock_for_document(db, company_id, current["id"], current.get("environment") or "sandbox", reverse=False, issued_at=persisted.get("issued_at"))

        if storage_path:
            db.rest_insert("document_files", {
                "folio": f"DOC-{company_id}-{uuid_sat or folio}-xml",
                "company_id": company_id,
                "cfdi_document_id": current["id"],
                "uuid": uuid_sat or None,
                "file_type": "xml",
                "storage_bucket": _BUCKET,
                "storage_path": storage_path,
                "content_type": "application/xml",
                "size_bytes": len((stamp_result.get("xml") or "").encode("utf-8")),
            })

        warnings = []
        if is_simulated:
            warnings.append("sandbox_simulated: uuid de prueba, no es un timbre fiscal real — status=simulated, no stamped")
        if not storage_path:
            warnings.append("No se pudo subir el XML al bucket — revisar supabase_storage_upload")

        if not is_simulated and uuid_sat:
            pdf_path = self._store_pdf(company_id, current, adapter, uuid_sat)
            if pdf_path:
                db.rest_update("cfdi_documents", values={"pdf_storage_path": pdf_path}, filters={"company_id": f"eq.{company_id}", "folio": f"eq.{folio}"})
                db.rest_insert("document_files", {
                    "folio": f"DOC-{company_id}-{uuid_sat}-pdf",
                    "company_id": company_id,
                    "cfdi_document_id": current["id"],
                    "uuid": uuid_sat,
                    "file_type": "pdf",
                    "storage_bucket": _BUCKET,
                    "storage_path": pdf_path,
                    "content_type": "application/pdf",
                })
                persisted["pdf_storage_path"] = pdf_path
            else:
                warnings.append("No se pudo obtener/subir el PDF del PAC — el XML si quedo guardado")

        return {"ok": True, "data": {"cfdi_document": persisted, "warnings": warnings}}

    def _store_pdf(self, company_id: str, current: dict, adapter: "PacAdapter", uuid_sat: str) -> str:
        try:
            res = adapter.download_pdf(uuid_sat)
        except NotImplementedError:
            return ""
        if not res.get("ok"):
            return ""
        pdf_b64 = (res.get("data") or {}).get("pdf_b64") or ""
        if not pdf_b64:
            return ""
        environment = current.get("environment") or "sandbox"
        cfdi_type = current.get("cfdi_type") or "cfdi"
        now = datetime.now(timezone.utc)
        path = f"{company_id}/{environment}/{cfdi_type}/{now:%Y}/{now:%m}/{uuid_sat}.pdf"
        upload = _runner().run(
            "vertical_supabase/supabase_storage_upload",
            {"bucket": _BUCKET, "path": path, "content_b64": pdf_b64, "content_type": "application/pdf"},
        )
        return path if upload.get("ok") else ""

    def _cancel(self, db: SupabaseClient, context: dict, company_id: str, folio: str, current: dict) -> dict:
        status = current.get("status")
        if status not in ("stamped", "simulated"):
            return {"ok": False, "error": "cfdi_not_stamped", "data": {"detail": f"status actual: {status}, solo se puede cancelar stamped|simulated"}}
        if status == "cancelled":
            return {"ok": True, "data": {"cfdi_document": current, "warnings": ["already_cancelled"]}}

        motivo = str(context.get("motivo") or "02").strip()
        uuid_sat = current.get("uuid") or ""

        # Motivo 01 (comprobante emitido con errores CON relacion) exige que
        # el CFDI sustituto ya exista, timbrado, y traiga CfdiRelacionados
        # tipo 04 apuntando a este UUID — si no, el receptor pierde el
        # comprobante fiscal sin sustituto valido (regla RMF vigente).
        related_cfdi_uuid = str(context.get("related_cfdi_uuid") or "").strip()
        if motivo == "01":
            if not related_cfdi_uuid:
                return {"ok": False, "error": "motivo_01_requiere_related_cfdi_uuid", "data": {"detail": "cancelar con motivo 01 exige el UUID del CFDI sustituto ya timbrado (related_cfdi_uuid)"}}
            sub_res = db.rest_select(
                "cfdi_documents",
                filters={"company_id": f"eq.{company_id}", "uuid": f"eq.{related_cfdi_uuid}", "related_cfdi_uuid": f"eq.{uuid_sat}"},
                select="id,status", limit=1,
            )
            substitute = (sub_res.get("data") or [None])[0] if sub_res.get("ok") else None
            if not substitute or substitute.get("status") not in ("stamped", "simulated"):
                return {"ok": False, "error": "sustituto_no_encontrado", "data": {"detail": "no se encontro un CFDI timbrado que declare related_cfdi_uuid=este folio y relation_type=04 — timbra primero el sustituto"}}

        if status == "simulated":
            cancel_result = {"ok": True}
        else:
            adapter_context = {**context}
            adapter_context.setdefault("pac_provider", current.get("pac_provider"))
            adapter = get_pac_adapter(adapter_context, company_id)
            if adapter is None:
                return {"ok": False, "error": "pac_not_configured"}
            try:
                cancel_result = adapter.cancel(uuid_sat, motivo, related_cfdi_uuid or None)
            except NotImplementedError as exc:
                cancel_result = {"ok": False, "error": str(exc)}

        if not cancel_result.get("ok"):
            return {"ok": False, "error": "pac_cancel_error", "data": {"detail": cancel_result.get("error")}}

        upd = db.rest_update(
            "cfdi_documents",
            values={
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "related_cfdi_uuid": related_cfdi_uuid or current.get("related_cfdi_uuid"),
                "related_cfdi_relation_type": "04" if related_cfdi_uuid else current.get("related_cfdi_relation_type"),
            },
            filters={"company_id": f"eq.{company_id}", "folio": f"eq.{folio}"},
        )
        if not upd.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": upd.get("error")}}

        self._apply_stock_for_document(db, company_id, current["id"], current.get("environment") or "sandbox", reverse=True, issued_at=None)

        return {"ok": True, "data": {"cfdi_document": (upd.get("data") or [current])[0]}}

    def _check_status(self, context: dict, company_id: str, current: dict) -> dict:
        uuid_sat = current.get("uuid") or ""
        if not uuid_sat or current.get("status") in ("draft", "simulated"):
            return {"ok": True, "data": {"status": current.get("status"), "pac_status": None}}
        adapter_context = {**context}
        adapter_context.setdefault("pac_provider", current.get("pac_provider"))
        adapter = get_pac_adapter(adapter_context, company_id)
        if adapter is None:
            return {"ok": False, "error": "pac_not_configured"}
        try:
            res = adapter.get_cfdi(uuid_sat)
        except NotImplementedError as exc:
            return {"ok": False, "error": str(exc)}
        if not res.get("ok"):
            return {"ok": False, "error": "pac_error", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"status": current.get("status"), "pac_status": res.get("data")}}

    def _apply_stock_for_document(self, db: SupabaseClient, company_id: str, cfdi_document_id: str, environment: str, reverse: bool, issued_at: str | None) -> None:
        """Inventario propio de Factu4All (independiente del ERP). El saldo no
        se incrementa en tiempo real: cada item con product_id se etiqueta con
        su almacen y se dispara vertical_factu4all/inventory_recalculate para
        el mes fiscal correspondiente, que recalcula ese mes y repropaga hacia
        adelante. Al cancelar, se revierte via un movimiento out_cancelled
        NUEVO fechado hoy (la cancelacion es un evento fiscal de hoy, no una
        edicion retroactiva del mes original) — nunca se borra el original."""
        mv_res = db.rest_select(
            "cfdi_item_movements",
            filters={"cfdi_document_id": f"eq.{cfdi_document_id}", "movement_direction": "eq.out"},
            select="*",
        )
        if not mv_res.get("ok"):
            return
        warehouse_id = self._default_warehouse(company_id)
        if not warehouse_id:
            return
        for movement in mv_res.get("data") or []:
            product_id = movement.get("product_id")
            quantity = float(movement.get("quantity") or 0)
            if not product_id or quantity <= 0:
                continue
            # Solo mercancia mueve inventario/costeo — un servicio o venta de
            # activo fijo se queda registrado en el kardex fiscal pero no en
            # almacen. Igual se fecha (issued_at) para que la boveda lo liste
            # correctamente aunque no toque stock.
            is_merchandise = movement.get("classification_group_snapshot") == "mercancia"

            if not reverse:
                stamp_issued_at = issued_at or datetime.now(timezone.utc).isoformat()
                values = {"environment": environment, "issued_at": stamp_issued_at}
                if is_merchandise:
                    values["warehouse_id"] = warehouse_id
                db.rest_update("cfdi_item_movements", values=values, filters={"id": f"eq.{movement['id']}"})
                recalc_from = stamp_issued_at
            elif is_merchandise:
                now_iso = datetime.now(timezone.utc).isoformat()
                db.rest_insert("cfdi_item_movements", {
                    **{k: v for k, v in movement.items() if k not in ("id", "created_at", "folio", "balance_after")},
                    "folio": f"{movement['folio']}-CANCEL",
                    "movement_direction": "out_cancelled",
                    "environment": environment,
                    "warehouse_id": warehouse_id,
                    "issued_at": now_iso,
                    "cancelled_at": now_iso,
                    "cancels_movement_id": movement["id"],
                })
                recalc_from = now_iso
            else:
                continue

            if not is_merchandise:
                continue
            self._trigger_recalculate(company_id, product_id, warehouse_id, environment, recalc_from)
            _runner().run("vertical_factu4all/inventory_cost_recalculate", {
                "company_id": company_id, "product_id": product_id, "warehouse_id": warehouse_id,
                "environment": environment, "dry_run": False,
            })

    def _default_warehouse(self, company_id: str) -> str:
        res = _runner().run("vertical_factu4all/warehouse_manage", {"action": "ensure_default", "company_id": company_id})
        if not res.get("ok"):
            return ""
        return (res.get("data") or {}).get("warehouse", {}).get("id") or ""

    def _trigger_recalculate(self, company_id: str, product_id: str, warehouse_id: str, environment: str, issued_at_iso: str) -> None:
        try:
            year, month = int(issued_at_iso[0:4]), int(issued_at_iso[5:7])
        except (ValueError, IndexError):
            now = datetime.now(timezone.utc)
            year, month = now.year, now.month
        _runner().run("vertical_factu4all/inventory_recalculate", {
            "company_id": company_id, "product_id": product_id, "warehouse_id": warehouse_id,
            "environment": environment, "from_year": year, "from_month": month, "dry_run": False,
        })

    def _folio_number(self, cfdi_folio: str | None, series: str | None) -> str:
        cfdi_folio = cfdi_folio or ""
        series = series or ""
        if series and cfdi_folio.startswith(series):
            return cfdi_folio[len(series):].lstrip("0") or "0"
        return cfdi_folio

    def _fetch_stamp_context(self, db: SupabaseClient, current: dict) -> tuple[dict, dict, list, list[str]]:
        """Reglas de timbrado del diseno: emisor, receptor, pago e items
        completos antes de timbrar. No llama al PAC. Regresa (issuer, party,
        items, missing) — issuer/party/items se reusan para armar el payload
        real de Facturama, no solo para validar."""
        missing: list[str] = []

        issuer: dict = {}
        issuer_profile_id = current.get("issuer_profile_id")
        if not issuer_profile_id:
            missing.append("issuer_profile_id")
        else:
            issuer_res = db.rest_select("issuer_profiles", filters={"id": f"eq.{issuer_profile_id}"}, select="rfc,legal_name,fiscal_regime,expedition_place", limit=1)
            issuer = (issuer_res.get("data") or [{}])[0] if issuer_res.get("ok") else {}
            for field in ("rfc", "legal_name", "fiscal_regime", "expedition_place"):
                if not issuer.get(field):
                    missing.append(f"issuer.{field}")

        party: dict = {}
        party_id = current.get("party_id")
        if not party_id:
            missing.append("party_id")
        else:
            party_res = db.rest_select("parties", filters={"id": f"eq.{party_id}"}, select="rfc,legal_name,tax_regime,tax_zip_code,cfdi_use_default", limit=1)
            party = (party_res.get("data") or [{}])[0] if party_res.get("ok") else {}
            for field in ("rfc", "legal_name", "tax_regime", "tax_zip_code", "cfdi_use_default"):
                if not party.get(field):
                    missing.append(f"party.{field}")

        for field in ("payment_method", "payment_form", "currency"):
            if not current.get(field):
                missing.append(field)

        items_res = db.rest_select("cfdi_item_movements", filters={"cfdi_document_id": f"eq.{current['id']}"}, select="*")
        items = items_res.get("data") or [] if items_res.get("ok") else []
        if not items:
            missing.append("items")
        for index, item in enumerate(items, start=1):
            if not item.get("sat_product_key_snapshot"):
                missing.append(f"items[{index}].sat_product_key")
            if not item.get("sat_unit_key_snapshot"):
                missing.append(f"items[{index}].sat_unit_key")
            if not item.get("tax_object_snapshot"):
                missing.append(f"items[{index}].tax_object")
            if not (item.get("quantity") and float(item["quantity"]) > 0):
                missing.append(f"items[{index}].quantity")
            if item.get("unit_price") is None:
                missing.append(f"items[{index}].unit_price")

        return issuer, party, items, missing

    def _store_xml(self, company_id: str, current: dict, file_key: str, xml: str) -> str:
        """Sube el XML a Supabase Storage (bucket privado factu4all-documents),
        nunca a disco local — /tmp no persiste entre requests/deploys."""
        if not xml:
            return ""
        environment = current.get("environment") or "sandbox"
        cfdi_type = current.get("cfdi_type") or "cfdi"
        now = datetime.now(timezone.utc)
        path = f"{company_id}/{environment}/{cfdi_type}/{now:%Y}/{now:%m}/{file_key}.xml"
        res = _runner().run(
            "vertical_supabase/supabase_storage_upload",
            {
                "bucket": _BUCKET,
                "path": path,
                "content_b64": base64.b64encode(xml.encode("utf-8")).decode(),
                "content_type": "application/xml",
            },
        )
        if not res.get("ok"):
            return ""
        return path
