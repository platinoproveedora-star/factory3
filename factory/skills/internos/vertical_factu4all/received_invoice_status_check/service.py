from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"
_SAT_URL = "https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc"
_ACCEPT_WINDOW_HOURS = 72


class ReceivedInvoiceStatusCheckService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        action = str(context.get("action") or "check").strip().lower()
        db = SupabaseClient({**context, "schema": _SCHEMA})

        if action == "accept":
            return self._respond(db, context, company_id, "aceptada")
        if action == "reject":
            return self._respond(db, context, company_id, "rechazada")
        if action == "list_pending":
            return self._list_pending(db, company_id)
        return self._check(db, context, company_id)

    def _check(self, db: SupabaseClient, context: dict, company_id: str) -> dict:
        uuid_val = str(context.get("uuid") or "").strip()
        filters = {"company_id": f"eq.{company_id}", "direction": "eq.received", "sat_status": "eq.vigente"}
        if uuid_val:
            filters["uuid"] = f"eq.{uuid_val}"
        res = db.rest_select("cfdi_documents", filters=filters, select="id,uuid,folio,party_rfc_snapshot,issuer_rfc_snapshot,total", limit=200)
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}

        checked, newly_cancelled, errors = [], [], []
        now_iso = datetime.now(timezone.utc).isoformat()
        for doc in res.get("data") or []:
            if not doc.get("uuid"):
                continue
            sat_res = self._verify_sat(doc.get("party_rfc_snapshot") or "", company_id, doc.get("total") or 0, doc["uuid"])
            if not sat_res.get("ok"):
                errors.append({"uuid": doc["uuid"], "error": sat_res.get("error")})
                continue
            estado = sat_res.get("estado")
            checked.append({"uuid": doc["uuid"], "folio": doc["folio"], "estado": estado})
            if estado == "Cancelado":
                deadline = (datetime.now(timezone.utc) + timedelta(hours=_ACCEPT_WINDOW_HOURS)).isoformat()
                db.rest_update(
                    "cfdi_documents",
                    values={"sat_status": "cancelacion_pendiente", "sat_status_checked_at": now_iso, "cancellation_deadline_at": deadline},
                    filters={"id": f"eq.{doc['id']}"},
                )
                newly_cancelled.append(doc["uuid"])
            else:
                db.rest_update("cfdi_documents", values={"sat_status_checked_at": now_iso}, filters={"id": f"eq.{doc['id']}"})

        return {"ok": True, "data": {"checked": checked, "newly_cancelled": newly_cancelled, "errors": errors}}

    def _respond(self, db: SupabaseClient, context: dict, company_id: str, response: str) -> dict:
        uuid_val = str(context.get("uuid") or "").strip()
        if not uuid_val:
            return {"ok": False, "error": "uuid_requerido"}
        doc_res = db.rest_select("cfdi_documents", filters={"company_id": f"eq.{company_id}", "uuid": f"eq.{uuid_val}", "direction": "eq.received"}, select="id,sat_status", limit=1)
        if not doc_res.get("ok") or not doc_res.get("data"):
            return {"ok": False, "error": "documento_no_encontrado"}
        doc = doc_res["data"][0]
        if doc.get("sat_status") != "cancelacion_pendiente":
            return {"ok": False, "error": "sin_cancelacion_pendiente", "data": {"detail": f"sat_status actual: {doc.get('sat_status')}"}}

        values = {"cancellation_response": response}
        values["sat_status"] = "cancelado" if response == "aceptada" else "vigente"
        if response == "aceptada":
            values["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        upd = db.rest_update("cfdi_documents", values=values, filters={"id": f"eq.{doc['id']}"})
        if not upd.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": upd.get("error")}}
        return {"ok": True, "data": {"cfdi_document": (upd.get("data") or [None])[0]}}

    def _list_pending(self, db: SupabaseClient, company_id: str) -> dict:
        res = db.rest_select(
            "cfdi_documents",
            filters={"company_id": f"eq.{company_id}", "direction": "eq.received", "sat_status": "eq.cancelacion_pendiente"},
            select="*", order="cancellation_deadline_at.asc",
        )
        if not res.get("ok"):
            return {"ok": False, "error": "db_query_failed", "data": {"detail": res.get("error")}}
        return {"ok": True, "data": {"pending": res.get("data") or []}}

    def _verify_sat(self, rfc_emisor: str, rfc_receptor_company_id: str, total, uuid_val: str) -> dict:
        """Servicio publico de verificacion de CFDI del SAT — no requiere
        credenciales. NO probado contra el servicio real todavia (sandbox sin
        salida a internet verificada); envelope SOAP documentado publicamente,
        validar en cuanto haya un UUID real disponible."""
        import urllib.error
        import urllib.request

        expresion = f"?re={rfc_emisor}&rr={rfc_receptor_company_id}&tt={float(total or 0):.6f}&id={uuid_val}"
        expresion_xml = expresion.replace("&", "&amp;")
        body = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            "<s:Envelope xmlns:s=\"http://www.w3.org/2003/05/soap-envelope\">"
            "<s:Body><ConsultaCFDIService xmlns=\"http://tempuri.org\">"
            f"<expresionImpresa>{expresion_xml}</expresionImpresa>"
            "</ConsultaCFDIService></s:Body></s:Envelope>"
        )
        req = urllib.request.Request(
            _SAT_URL,
            data=body.encode("utf-8"),
            headers={
                "Content-Type": "application/soap+xml; charset=utf-8",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                text = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": f"SAT HTTP {exc.code}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        estado_match = re.search(r"<[^>]*Estado>([^<]*)</[^>]*Estado>", text)
        if not estado_match:
            return {"ok": False, "error": "respuesta_sat_no_reconocida", "data": {"detail": text[:300]}}
        return {"ok": True, "estado": estado_match.group(1).strip()}
