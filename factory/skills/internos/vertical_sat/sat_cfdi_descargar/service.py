"""Descarga paquete ZIP del SAT y extrae lista de XML de CFDIs."""
from __future__ import annotations

import base64
import hashlib
import io
import os
import urllib.request
import uuid as _uuid_mod
import zipfile

_URL    = "https://cfdidescargamasiva.clouda.sat.gob.mx/DescargarPaquete/DescargarPaqueteService.svc"
_ACTION = '"http://DescargaMasivaTerceros.gob.mx/IDescargarPaqueteService/DescargarPaquete"'
_NS_DS  = "http://www.w3.org/2000/09/xmldsig#"
_NS_DES = "http://DescargaMasivaTerceros.gob.mx"


def _cargar_efirma(cer_b64: str, key_b64: str, key_pwd: str):
    from cryptography.hazmat.primitives import serialization
    cer_der = base64.b64decode(cer_b64)
    key_der = base64.b64decode(key_b64)
    privkey = serialization.load_der_private_key(key_der, password=key_pwd.encode())
    return privkey, cer_der


def _firmar_elemento(elem_xml: str, cer_der: bytes, privkey, elem_id: str) -> str:
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


class SatCfdiDescargarService:

    def ejecutar(self, context: dict) -> dict:
        token      = context.get("token", "")
        rfc        = context.get("rfc")          or os.getenv("SAT_RFC", "")
        cer_b64    = context.get("cer_b64")      or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64    = context.get("key_b64")      or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd    = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")
        id_paquete = context.get("id_paquete", "")

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"xmls": [], "total": 0}}

        if not all([token, rfc, cer_b64, key_b64, key_pwd, id_paquete]):
            return {"ok": False, "error": "Faltan: token, rfc, efirma creds, id_paquete"}

        try:
            privkey, cer_der = _cargar_efirma(cer_b64, key_b64, key_pwd)
        except Exception as e:
            return {"ok": False, "error": f"Error cargando e.firma: {e}"}

        try:
            xmls = self._descargar(token, rfc, privkey, cer_der, id_paquete)
            return {
                "ok":      True,
                "message": f"{len(xmls)} XMLs extraídos del paquete",
                "data":    {"xmls": xmls, "total": len(xmls), "id_paquete": id_paquete},
            }
        except Exception as e:
            return {"ok": False, "error": f"Error descargando paquete SAT: {e}"}

    def _descargar(self, token, rfc, privkey, cer_der, id_paquete) -> list[str]:
        from lxml import etree

        desc_id  = f"descarga-{_uuid_mod.uuid4().hex[:8]}"
        desc_xml = (
            f'<des:peticionDescarga xmlns:des="{_NS_DES}" Id="{desc_id}"'
            f' IdPaquete="{id_paquete}" RfcSolicitante="{rfc}"/>'
        )
        firma     = _firmar_elemento(desc_xml, cer_der, privkey, desc_id)
        desc_elem = etree.fromstring(desc_xml.encode())
        desc_elem.append(etree.fromstring(firma.encode()))
        desc_signed = etree.tostring(desc_elem, encoding="unicode")

        envelope = (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<s:Body>'
            f'<des:DescargarPaquete xmlns:des="{_NS_DES}">'
            f'{desc_signed}'
            f'</des:DescargarPaquete>'
            f'</s:Body>'
            f'</s:Envelope>'
        )
        req = urllib.request.Request(
            _URL,
            data=envelope.encode("utf-8"),
            headers={
                "Content-Type":  'text/xml; charset="utf-8"',
                "SOAPAction":    _ACTION,
                "Authorization": f'WRAP access_token="{token}"',
                "User-Agent":    "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")

        root   = etree.fromstring(body.encode())
        result = root.find(f".//{{{_NS_DES}}}DescargarPaqueteResult")
        if result is None:
            raise ValueError(f"Respuesta inesperada: {body[:500]}")

        cod = result.get("CodEstatus", "")
        if cod != "5000":
            raise ValueError(f"SAT error {cod}: {result.get('Mensaje','')}")

        paquete_b64 = result.get("Paquete") or ""
        if not paquete_b64:
            return []

        zip_bytes = base64.b64decode(paquete_b64)
        xmls      = []
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for name in zf.namelist():
                if name.lower().endswith(".xml"):
                    xmls.append(zf.read(name).decode("utf-8", errors="replace"))
        return xmls
