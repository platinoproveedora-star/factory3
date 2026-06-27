"""Solicita paquete de descarga masiva al SAT (tipo E=emitidos / R=recibidos)."""
from __future__ import annotations

import base64
import hashlib
import os
import urllib.request
import uuid as _uuid_mod

# SAT cambió la URL en 2025; si la principal da 404 se intenta la alternativa
_URL      = "https://cfdidescargamasiva.clouda.sat.gob.mx/SolicitaDescargaService.svc"
_URL_ALT  = "https://cfdidescargamasivapr.clouda.sat.gob.mx/SolicitaDescargaService.svc"
_ACTION = '"http://DescargaMasivaTerceros.gob.mx/ISolicitaDescargaService/SolicitaDescarga"'
_NS_DS  = "http://www.w3.org/2000/09/xmldsig#"
_NS_DES = "http://DescargaMasivaTerceros.gob.mx"


def _cargar_efirma(cer_b64: str, key_b64: str, key_pwd: str):
    from cryptography.hazmat.primitives import serialization
    cer_der = base64.b64decode(cer_b64)
    key_der = base64.b64decode(key_b64)
    privkey = serialization.load_der_private_key(key_der, password=key_pwd.encode())
    return privkey, cer_der


def _firmar_elemento(elem_xml: str, cer_der: bytes, privkey, elem_id: str) -> str:
    """Firma el elemento XML (enveloped-signature) y retorna el bloque Signature."""
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
        f'<Reference URI="#{elem_id}">'
        f'<Transforms>'
        f'<Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>'
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

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"id_solicitud": "dry_solicitud_id"}}

        if not all([token, rfc, cer_b64, key_b64, key_pwd, fecha_inicio, fecha_fin]):
            return {"ok": False, "error": "Faltan: token, rfc, efirma creds, fecha_inicio, fecha_fin"}

        try:
            privkey, cer_der = _cargar_efirma(cer_b64, key_b64, key_pwd)
        except Exception as e:
            return {"ok": False, "error": f"Error cargando e.firma: {e}"}

        try:
            id_solicitud = self._solicitar(token, rfc, privkey, cer_der,
                                           fecha_inicio, fecha_fin, tipo, tipo_comp)
            return {
                "ok":      True,
                "message": f"Solicitud aceptada: {id_solicitud}",
                "data":    {"id_solicitud": id_solicitud, "tipo": tipo, "rfc": rfc},
            }
        except Exception as e:
            return {"ok": False, "error": f"Error solicitud SAT: {e}"}

    def _solicitar(self, token, rfc, privkey, cer_der,
                   fi, ff, tipo, tipo_comp) -> str:
        from lxml import etree

        sol_id = f"solicitud-{_uuid_mod.uuid4().hex[:8]}"
        rfc_emisor   = f'RfcEmisor="{rfc}"'    if tipo == "E" else ""
        rfc_receptor = f'RfcReceptores="{rfc}"' if tipo == "R" else ""
        tc_attr      = f'TipoComprobante="{tipo_comp}"' if tipo_comp else ""
        # SAT exige EstadoComprobante="Vigente" en solicitudes de recibidos (R)
        # desde 2025-05-30 — sin este atributo el SAT devuelve cod 5004.
        estado_comp  = 'EstadoComprobante="Vigente"' if tipo == "R" else ""

        sol_xml = (
            f'<des:solicitud xmlns:des="{_NS_DES}" Id="{sol_id}"'
            f' RfcSolicitante="{rfc}"'
            f' FechaInicial="{fi}T00:00:00"'
            f' FechaFinal="{ff}T23:59:59"'
            f' TipoSolicitud="CFDI"'
            f' {rfc_emisor} {rfc_receptor} {tc_attr} {estado_comp}/>'
        )

        firma   = _firmar_elemento(sol_xml, cer_der, privkey, sol_id)
        sol_elem = etree.fromstring(sol_xml.encode())
        sig_elem = etree.fromstring(firma.encode())
        sol_elem.append(sig_elem)
        sol_signed = etree.tostring(sol_elem, encoding="unicode")

        envelope = (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<s:Header>'
            f'<h:SolicitaDescargaHeader xmlns:h="{_NS_DES}">'
            f'<RfcSolicitante>{rfc}</RfcSolicitante>'
            f'</h:SolicitaDescargaHeader>'
            f'</s:Header>'
            f'<s:Body>'
            f'<des:SolicitaDescarga xmlns:des="{_NS_DES}">'
            f'{sol_signed}'
            f'</des:SolicitaDescarga>'
            f'</s:Body>'
            f'</s:Envelope>'
        )

        import urllib.error
        body = None
        for _url in (_URL, _URL_ALT):
            req = urllib.request.Request(
                _url,
                data=envelope.encode("utf-8"),
                headers={
                    "Content-Type":  'text/xml; charset="utf-8"',
                    "SOAPAction":    _ACTION,
                    "Authorization": f'WRAP access_token="{token}"',
                    "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read().decode("utf-8")
                break
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                if e.code == 404:
                    continue  # intentar URL alternativa
                raise ValueError(f"SAT HTTP {e.code}: {err_body[:300]}")
        if body is None:
            raise ValueError(f"SAT no disponible en ninguna URL ({_URL} y {_URL_ALT} devolvieron 404)")

        root   = etree.fromstring(body.encode())
        result = root.find(f".//{{{_NS_DES}}}SolicitaDescargaResult")
        if result is None:
            raise ValueError(f"Respuesta inesperada: {body[:500]}")

        cod = result.get("CodEstatus", "")
        id_ = result.get("IdSolicitud", "")
        msg = result.get("Mensaje", "")
        if cod not in ("5000", "5002"):
            raise ValueError(f"SAT error {cod}: {msg}")
        return id_
