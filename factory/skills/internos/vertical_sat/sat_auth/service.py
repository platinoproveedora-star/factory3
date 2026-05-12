"""Autenticación SAT Descarga Masiva via e.firma (SOAP + WS-Security XML-DSig)."""
from __future__ import annotations

import base64
import hashlib
import os
import urllib.request
import uuid
from datetime import datetime, timezone, timedelta

_AUTH_URL    = "https://cfdidescargamasiva.clouda.sat.gob.mx/Autenticacion/Autenticacion.svc"
_SOAP_ACTION = '"http://DescargaMasivaTerceros.gob.mx/IAutenticacion/Autentica"'
_NS_U  = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
_NS_O  = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
_NS_DS = "http://www.w3.org/2000/09/xmldsig#"


def _cargar_efirma(cer_b64: str, key_b64: str, key_pwd: str):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    cer_der = base64.b64decode(cer_b64)
    key_der = base64.b64decode(key_b64)
    cert    = x509.load_der_x509_certificate(cer_der)
    privkey = serialization.load_der_private_key(key_der, password=key_pwd.encode())
    return cert, privkey, cer_der


def _firmar_timestamp(ts_xml: str, cer_der: bytes, privkey, ts_id: str, tok_id: str) -> str:
    from lxml import etree
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding as _padding

    ts_elem = etree.fromstring(ts_xml.encode())
    ts_c14n = etree.tostring(ts_elem, method="c14n", exclusive=True, with_comments=False)
    digest  = base64.b64encode(hashlib.sha1(ts_c14n).digest()).decode()

    si_xml = (
        f'<SignedInfo xmlns="{_NS_DS}">'
        f'<CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>'
        f'<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>'
        f'<Reference URI="#{ts_id}">'
        f'<Transforms><Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/></Transforms>'
        f'<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>'
        f'<DigestValue>{digest}</DigestValue>'
        f'</Reference>'
        f'</SignedInfo>'
    )
    si_elem = etree.fromstring(si_xml.encode())
    si_c14n = etree.tostring(si_elem, method="c14n", exclusive=True, with_comments=False)
    sig_val = base64.b64encode(privkey.sign(si_c14n, _padding.PKCS1v15(), hashes.SHA1())).decode()

    return (
        f'<Signature xmlns="{_NS_DS}">'
        f'{si_xml}'
        f'<SignatureValue>{sig_val}</SignatureValue>'
        f'<KeyInfo>'
        f'<o:SecurityTokenReference xmlns:o="{_NS_O}">'
        f'<o:Reference ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"'
        f' URI="#{tok_id}"/>'
        f'</o:SecurityTokenReference>'
        f'</KeyInfo>'
        f'</Signature>'
    )


class SatAuthService:

    def ejecutar(self, context: dict) -> dict:
        rfc     = context.get("rfc")          or os.getenv("SAT_RFC", "")
        cer_b64 = context.get("cer_b64")      or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64 = context.get("key_b64")      or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"token": "dry_token", "rfc": rfc or "RFC_NO_CONF"}}

        if not all([rfc, cer_b64, key_b64, key_pwd]):
            return {"ok": False, "error": "Faltan: SAT_RFC, SAT_EFIRMA_CER_B64, SAT_EFIRMA_KEY_B64, SAT_EFIRMA_PASSWORD"}

        try:
            _cert, privkey, cer_der = _cargar_efirma(cer_b64, key_b64, key_pwd)
        except Exception as e:
            return {"ok": False, "error": f"Error cargando e.firma: {e}"}

        try:
            token = self._autenticar(privkey, cer_der)
            return {"ok": True, "message": "Token SAT obtenido", "data": {"token": token, "rfc": rfc}}
        except Exception as e:
            return {"ok": False, "error": f"Error SAT auth: {e}"}

    def _autenticar(self, privkey, cer_der: bytes) -> str:
        now      = datetime.now(timezone.utc)
        fmt      = "%Y-%m-%dT%H:%M:%S.000Z"
        ts_id    = "_0"
        tok_id   = f"uuid-{uuid.uuid4()}-1"
        created  = now.strftime(fmt)
        expires  = (now + timedelta(minutes=5)).strftime(fmt)
        cert_b64 = base64.b64encode(cer_der).decode()

        ts_xml = (
            f'<u:Timestamp u:Id="{ts_id}" xmlns:u="{_NS_U}">'
            f'<u:Created>{created}</u:Created>'
            f'<u:Expires>{expires}</u:Expires>'
            f'</u:Timestamp>'
        )
        firma = _firmar_timestamp(ts_xml, cer_der, privkey, ts_id, tok_id)

        envelope = (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" xmlns:u="{_NS_U}">'
            f'<s:Header>'
            f'<o:Security s:mustUnderstand="1" xmlns:o="{_NS_O}">'
            f'{ts_xml}'
            f'<o:BinarySecurityToken u:Id="{tok_id}"'
            f' ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"'
            f' EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">'
            f'{cert_b64}'
            f'</o:BinarySecurityToken>'
            f'{firma}'
            f'</o:Security>'
            f'</s:Header>'
            f'<s:Body>'
            f'<Autentica xmlns="http://DescargaMasivaTerceros.gob.mx"/>'
            f'</s:Body>'
            f'</s:Envelope>'
        )

        req = urllib.request.Request(
            _AUTH_URL,
            data=envelope.encode("utf-8"),
            headers={
                "Content-Type": 'text/xml; charset="utf-8"',
                "SOAPAction":   _SOAP_ACTION,
                "User-Agent":   "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")

        from lxml import etree
        root   = etree.fromstring(body.encode())
        result = root.find(".//{http://DescargaMasivaTerceros.gob.mx}AutenticaResult")
        if result is None or not result.text:
            raise ValueError(f"Sin token en respuesta SAT: {body[:500]}")
        return result.text.strip()
