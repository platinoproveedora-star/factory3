"""Solicita paquete de descarga masiva al SAT (tipo E=emitidos / R=recibidos)."""
from __future__ import annotations

import base64
import hashlib
import os
import re
import urllib.request
import uuid as _uuid_mod
from datetime import date, datetime
from zoneinfo import ZoneInfo

_URL    = "https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/SolicitaDescargaService.svc"
_NS_DS  = "http://www.w3.org/2000/09/xmldsig#"
_NS_DES = "http://DescargaMasivaTerceros.sat.gob.mx"
_RFC_RE = re.compile(r"^[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}$")


def _cargar_efirma(cer_b64: str, key_b64: str, key_pwd: str):
    from cryptography.hazmat.primitives import serialization
    cer_der = base64.b64decode(cer_b64)
    key_der = base64.b64decode(key_b64)
    privkey = serialization.load_der_private_key(key_der, password=key_pwd.encode())
    return privkey, cer_der


def _firmar_elemento(elem_xml: str, cer_der: bytes, privkey, elem_id: str) -> str:
    """Firma el elemento XML y retorna el bloque Signature."""
    from lxml import etree
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding as _p

    elem    = etree.fromstring(elem_xml.encode())
    c14n    = etree.tostring(elem, method="c14n", exclusive=True, with_comments=False)
    digest  = base64.b64encode(hashlib.sha1(c14n).digest()).decode()
    cert_b64 = base64.b64encode(cer_der).decode()

    si_xml = (
        f'<SignedInfo xmlns="{_NS_DS}">'
        f'<CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        f'<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>'
        f'<Reference URI="{elem_id}">'
        f'<Transforms>'
        f'<Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        f'</Transforms>'
        f'<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>'
        f'<DigestValue>{digest}</DigestValue>'
        f'</Reference>'
        f'</SignedInfo>'
    )
    si_elem = etree.fromstring(si_xml.encode())
    si_c14n = etree.tostring(si_elem, method="c14n", exclusive=True, with_comments=False)
    sig_val = base64.b64encode(privkey.sign(si_c14n, _p.PKCS1v15(), hashes.SHA1())).decode()

    return (
        f'<Signature xmlns="{_NS_DS}">'
        f'{si_xml}'
        f'<SignatureValue>{sig_val}</SignatureValue>'
        f'<KeyInfo><X509Data><X509Certificate>{cert_b64}</X509Certificate></X509Data></KeyInfo>'
        f'</Signature>'
    )


class SatCfdiSolicitudService:

    def ejecutar(self, context: dict) -> dict:
        token        = context.get("token", "")
        rfc          = context.get("rfc")          or os.getenv("SAT_RFC", "")
        cer_b64      = context.get("cer_b64")      or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64      = context.get("key_b64")      or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd      = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")
        fecha_inicio = context.get("fecha_inicio", "")
        fecha_fin    = context.get("fecha_fin", "")
        tipo         = context.get("tipo", "E")
        tipo_comp    = context.get("tipo_comprobante", "")
        tipo_sol     = context.get("tipo_solicitud") or context.get("request_type") or "CFDI"
        rfc          = str(rfc).strip().upper()
        rfc_match    = str(context.get("rfc_contraparte") or context.get("rfc_match") or "").strip().upper()

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"id_solicitud": "dry_solicitud_id"}}

        if not all([token, rfc, cer_b64, key_b64, key_pwd, fecha_inicio, fecha_fin]):
            return {"ok": False, "error": "Faltan: token, rfc, efirma creds, fecha_inicio, fecha_fin"}
        if not self._valid_rfc(rfc):
            return {"ok": False, "error": f"RFC solicitante invalido: {rfc}"}
        if rfc_match and not self._valid_rfc(rfc_match):
            return {"ok": False, "error": f"RFC cliente/proveedor invalido: {rfc_match}. Debe ser RFC, no nombre."}

        try:
            privkey, cer_der = _cargar_efirma(cer_b64, key_b64, key_pwd)
        except Exception as e:
            return {"ok": False, "error": f"Error cargando e.firma: {e}"}

        try:
            fecha_fin = self._clamp_fecha_fin(fecha_fin)
            id_solicitud = self._solicitar(token, rfc, privkey, cer_der,
                                           fecha_inicio, fecha_fin, tipo, tipo_comp, tipo_sol, rfc_match)
            return {
                "ok":      True,
                "message": f"Solicitud aceptada: {id_solicitud}",
                "data":    {"id_solicitud": id_solicitud, "tipo": tipo, "rfc": rfc},
            }
        except Exception as e:
            return {"ok": False, "error": f"Error solicitud SAT: {e}"}

    def _solicitar(self, token, rfc, privkey, cer_der,
                   fi, ff, tipo, tipo_comp, tipo_sol, rfc_match) -> str:
        from lxml import etree

        node_name = "SolicitaDescargaEmitidos" if tipo == "E" else "SolicitaDescargaRecibidos"
        soap_action = f'"http://DescargaMasivaTerceros.sat.gob.mx/ISolicitaDescargaService/{node_name}"'
        rfc_emisor   = f' RfcEmisor="{rfc}"' if tipo == "E" else (f' RfcEmisor="{rfc_match}"' if rfc_match else "")
        rfc_receptor = f' RfcReceptor="{rfc}"' if tipo == "R" else ""
        tc_attr      = f'TipoComprobante="{tipo_comp}"' if tipo_comp else ""
        xml_extra    = f'<des:RfcReceptores><des:RfcReceptor>{rfc_match}</des:RfcReceptor></des:RfcReceptores>' if tipo == "E" and rfc_match else ""

        # EstadoComprobante: solo aplica a Emitidos y solo si se pasa explícitamente.
        # Omitir por defecto — SAT devuelve todos (Vigente + Cancelado) y el valor
        # "Vigente" provoca CodEstatus=301 en algunas combinaciones de rango/RFC.
        estado_comp_val = (context.get("estado_comprobante") or "").strip() if tipo == "E" else ""
        estado_comp = f' EstadoComprobante="{estado_comp_val}"' if estado_comp_val else ""
        tc_attr_str = f" {tc_attr}" if tc_attr else ""
        sol_xml = (
            f'<des:{node_name} xmlns:des="{_NS_DES}">'
            f'<des:solicitud'
            f'{estado_comp}'
            f' FechaFinal="{ff}{self._hora_fin(ff)}"'
            f' FechaInicial="{fi}T00:00:00"'
            f' RfcSolicitante="{rfc}"'
            f' TipoSolicitud="{tipo_sol}"'
            f'{rfc_emisor}{rfc_receptor}{tc_attr_str}>'
            f'{xml_extra}'
            f'</des:solicitud>'
            f'</des:{node_name}>'
        )

        firma   = _firmar_elemento(sol_xml, cer_der, privkey, "")
        sol_elem = etree.fromstring(sol_xml.encode())
        sig_elem = etree.fromstring(firma.encode())
        sol_elem.find(f"{{{_NS_DES}}}solicitud").append(sig_elem)
        sol_signed = etree.tostring(sol_elem, encoding="unicode")

        envelope = (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<s:Header/>'
            f'<s:Body>'
            f'{sol_signed}'
            f'</s:Body>'
            f'</s:Envelope>'
        )

        import urllib.error
        req = urllib.request.Request(
            _URL,
            data=envelope.encode("utf-8"),
            headers={
                "Content-Type":  'text/xml; charset="utf-8"',
                "SOAPAction":    soap_action,
                "Authorization": f'WRAP access_token="{token}"',
                "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise ValueError(f"SAT HTTP {e.code} en {_URL} — {err_body[:400]}")

        root   = etree.fromstring(body.encode())
        result = root.find(f".//{{{_NS_DES}}}solicitaDescargaEmitidosResult")
        if result is None:
            result = root.find(f".//{{{_NS_DES}}}solicitaDescargaRecibidosResult")
        if result is None:
            result = root.find(f".//{{{_NS_DES}}}SolicitaDescargaEmitidosResult")
        if result is None:
            result = root.find(f".//{{{_NS_DES}}}SolicitaDescargaRecibidosResult")
        if result is None:
            raise ValueError(f"Respuesta inesperada: {body[:500]}")

        cod = result.get("CodEstatus") or result.get("codestatus") or ""
        id_ = result.get("IdSolicitud") or result.get("idsolicitud") or ""
        msg = result.get("Mensaje") or result.get("mensaje") or ""
        if cod not in ("5000", "5002"):
            raise ValueError(f"SAT error {cod}: {msg}")
        if cod == "5002" and not id_:
            raise ValueError(
                f"SAT: solicitud duplicada (5002) — ya existe una activa para este rango/RFC. "
                f"Espera 24-72h a que expire, o prueba con un rango diferente. ({msg})"
            )
        return id_

    def _clamp_fecha_fin(self, fecha_fin: str) -> str:
        try:
            requested = date.fromisoformat(str(fecha_fin))
        except Exception:
            return fecha_fin
        try:
            today_mx = datetime.now(ZoneInfo("America/Mexico_City")).date()
        except Exception:
            today_mx = date.today()
        if requested > today_mx:
            return today_mx.isoformat()
        return fecha_fin

    def _hora_fin(self, fecha: str) -> str:
        """Pasado → T23:59:59. Hoy → hora actual MX (nunca futuro). Futuro ya fue clampeado."""
        try:
            now_mx = datetime.now(ZoneInfo("America/Mexico_City"))
            if date.fromisoformat(fecha) >= now_mx.date():
                return now_mx.strftime("T%H:%M:%S")
        except Exception:
            pass
        return "T23:59:59"

    def _valid_rfc(self, value: str) -> bool:
        return bool(_RFC_RE.match(str(value or "").strip().upper()))
