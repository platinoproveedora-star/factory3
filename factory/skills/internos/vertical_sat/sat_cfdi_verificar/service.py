"""Verifica estado de solicitud SAT y retorna ids de paquetes listos."""
from __future__ import annotations

import base64
import hashlib
import os
import urllib.request
import uuid as _uuid_mod

_URL    = "https://cfdidescargamasiva.clouda.sat.gob.mx/VerificaSolicitudDescargaService.svc"
_ACTION = '"http://DescargaMasivaTerceros.gob.mx/IVerificaSolicitudDescargaService/VerificaSolicitudDescarga"'
_NS_DS  = "http://www.w3.org/2000/09/xmldsig#"
_NS_DES = "http://DescargaMasivaTerceros.gob.mx"

# Códigos SAT: 5000=terminada ok, 5001=aceptada, 5002=en proceso, 5003=terminada vacía
_ESTADO_OK      = {"5000"}
_ESTADO_ESPERAR = {"5001", "5002"}
_ESTADO_VACIO   = {"5003"}


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


class SatCfdiVerificarService:

    def ejecutar(self, context: dict) -> dict:
        token        = context.get("token", "")
        rfc          = context.get("rfc")          or os.getenv("SAT_RFC", "")
        cer_b64      = context.get("cer_b64")      or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64      = context.get("key_b64")      or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd      = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")
        id_solicitud = context.get("id_solicitud", "")

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"estado": "dry", "paquetes": [], "lista": []}}

        if not all([token, rfc, cer_b64, key_b64, key_pwd, id_solicitud]):
            return {"ok": False, "error": "Faltan: token, rfc, efirma creds, id_solicitud"}

        try:
            privkey, cer_der = _cargar_efirma(cer_b64, key_b64, key_pwd)
        except Exception as e:
            return {"ok": False, "error": f"Error cargando e.firma: {e}"}

        try:
            estado, paquetes, cod = self._verificar(token, rfc, privkey, cer_der, id_solicitud)
        except Exception as e:
            return {"ok": False, "error": f"Error verificando SAT: {e}"}

        lista = paquetes if cod in _ESTADO_OK else []
        return {
            "ok":      cod in _ESTADO_OK | _ESTADO_ESPERAR | _ESTADO_VACIO,
            "message": f"Estado {cod} — {estado} — {len(lista)} paquetes",
            "data": {
                "cod_estado":    cod,
                "estado":        estado,
                "listo":         cod in _ESTADO_OK,
                "esperar":       cod in _ESTADO_ESPERAR,
                "vacio":         cod in _ESTADO_VACIO,
                "paquetes":      lista,
                "id_solicitud":  id_solicitud,
            },
        }

    def _verificar(self, token, rfc, privkey, cer_der, id_solicitud) -> tuple:
        from lxml import etree

        ver_id  = f"verifica-{_uuid_mod.uuid4().hex[:8]}"
        ver_xml = (
            f'<des:verifica xmlns:des="{_NS_DES}" Id="{ver_id}"'
            f' IdSolicitud="{id_solicitud}" RfcSolicitante="{rfc}"/>'
        )
        firma    = _firmar_elemento(ver_xml, cer_der, privkey, ver_id)
        ver_elem = etree.fromstring(ver_xml.encode())
        ver_elem.append(etree.fromstring(firma.encode()))
        ver_signed = etree.tostring(ver_elem, encoding="unicode")

        envelope = (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<s:Body>'
            f'<des:VerificaSolicitudDescarga xmlns:des="{_NS_DES}">'
            f'{ver_signed}'
            f'</des:VerificaSolicitudDescarga>'
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")

        root   = etree.fromstring(body.encode())
        result = root.find(f".//{{{_NS_DES}}}VerificaSolicitudDescargaResult")
        if result is None:
            raise ValueError(f"Respuesta inesperada: {body[:500]}")

        cod_estado = result.get("CodEstatus", "")
        estado     = result.get("EstadoSolicitud", "")
        paquetes   = [p.text.strip() for p in result.findall(f"{{{_NS_DES}}}IdsPaquetes/{{{_NS_DES}}}string") if p.text]
        return estado, paquetes, cod_estado
