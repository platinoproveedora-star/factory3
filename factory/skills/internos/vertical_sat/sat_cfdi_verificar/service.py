"""Verifica estado de solicitud SAT y retorna ids de paquetes listos."""
from __future__ import annotations

import base64
import hashlib
import os
import urllib.request
import uuid as _uuid_mod

_URL    = "https://cfdidescargamasivasolicitud.clouda.sat.gob.mx/VerificaSolicitudDescargaService.svc"
_ACTION = '"http://DescargaMasivaTerceros.sat.gob.mx/IVerificaSolicitudDescargaService/VerificaSolicitudDescarga"'
_NS_DS  = "http://www.w3.org/2000/09/xmldsig#"
_NS_DES = "http://DescargaMasivaTerceros.sat.gob.mx"

# EstadoSolicitud: 1=Aceptada 2=En proceso 3=Terminada 4=Error 5=Rechazada 6=Vencida
_ESTADO_ESPERAR = {0, 1, 2}  # 0 = SAT aún no registró la solicitud
_ESTADO_LISTO   = {3}
_ESTADO_ERROR   = {4, 5, 6}
_ESTADO_NOMBRES = {1: "Aceptada", 2: "En proceso", 3: "Terminada",
                   4: "Error", 5: "Rechazada", 6: "Vencida"}
# CodigoEstadoSolicitud
_COD_SIN_CFDIS  = 5004
_COD_DUPLICADA  = 5005


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


class SatCfdiVerificarService:

    def ejecutar(self, context: dict) -> dict:
        token        = context.get("token", "")
        rfc          = context.get("rfc")          or os.getenv("SAT_RFC", "")
        cer_b64      = context.get("cer_b64")      or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64      = context.get("key_b64")      or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd      = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")
        id_solicitud = context.get("id_solicitud", "")

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {
                "estado": "dry", "paquetes": [], "listo": False, "esperar": True, "vacio": False,
            }}

        if not all([token, rfc, cer_b64, key_b64, key_pwd, id_solicitud]):
            return {"ok": False, "error": "Faltan: token, rfc, efirma creds, id_solicitud"}

        try:
            privkey, cer_der = _cargar_efirma(cer_b64, key_b64, key_pwd)
        except Exception as e:
            return {"ok": False, "error": f"Error cargando e.firma: {e}"}

        try:
            estado_sol, cod_sol, num_cfdis, paquetes, mensaje = self._verificar(
                token, rfc, privkey, cer_der, id_solicitud
            )
        except Exception as e:
            return {"ok": False, "error": f"Error verificando SAT: {e}"}

        estado_txt = _ESTADO_NOMBRES.get(estado_sol, f"Desconocido({estado_sol})")
        listo   = estado_sol in _ESTADO_LISTO and bool(paquetes)
        vacio   = estado_sol in _ESTADO_LISTO and (not paquetes or cod_sol == _COD_SIN_CFDIS)
        esperar = estado_sol in _ESTADO_ESPERAR
        error   = estado_sol in _ESTADO_ERROR

        nota = ""
        if cod_sol == _COD_DUPLICADA:
            nota = " (solicitud duplicada — ya existe una vigente con los mismos parámetros)"
        elif cod_sol == _COD_SIN_CFDIS:
            nota = " (sin CFDIs en ese rango)"

        return {
            "ok":      not error,
            "message": f"EstadoSolicitud={estado_sol} ({estado_txt}) CodSol={cod_sol} {num_cfdis} CFDIs{nota}",
            "data": {
                "estado_solicitud": estado_sol,
                "estado":           estado_txt,
                "cod_solicitud":    cod_sol,
                "num_cfdis":        num_cfdis,
                "mensaje":          mensaje,
                "listo":            listo,
                "esperar":          esperar,
                "vacio":            vacio,
                "error_sat":        error,
                "paquetes":         paquetes if listo else [],
                "id_solicitud":     id_solicitud,
            },
        }

    def _verificar(self, token, rfc, privkey, cer_der, id_solicitud) -> tuple:
        from lxml import etree

        ver_xml = (
            f'<des:VerificaSolicitudDescarga xmlns:des="{_NS_DES}">'
            f'<des:solicitud IdSolicitud="{id_solicitud}" RfcSolicitante="{rfc}"></des:solicitud>'
            f'</des:VerificaSolicitudDescarga>'
        )
        firma    = _firmar_elemento(ver_xml, cer_der, privkey, "")
        ver_elem = etree.fromstring(ver_xml.encode())
        ver_elem.find(f"{{{_NS_DES}}}solicitud").append(etree.fromstring(firma.encode()))
        ver_signed = etree.tostring(ver_elem, encoding="unicode")

        envelope = (
            f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<s:Header/>'
            f'<s:Body>'
            f'{ver_signed}'
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

        # CodEstatus = estado de la LLAMADA (5000=ok); distinto de CodigoEstadoSolicitud
        cod_llamada = (result.get("CodEstatus") or result.get("codestatus") or "").strip()
        estado_sol  = int(result.get("EstadoSolicitud") or result.get("estadosolicitud") or 0)
        cod_sol     = int(result.get("CodigoEstadoSolicitud") or result.get("codigoestadosolicitud") or 0)
        num_cfdis   = int(result.get("NumeroCFDIs") or result.get("numerocfdis") or 0)
        mensaje     = result.get("Mensaje") or result.get("mensaje") or ""

        if cod_llamada and cod_llamada != "5000":
            raise ValueError(f"SAT verificar CodEstatus={cod_llamada}: {mensaje}")

        paquetes = [
            p.text.strip()
            for p in result.xpath(".//*[local-name()='IdsPaquetes']")
            if p.text and p.text.strip()
        ]
        return estado_sol, cod_sol, num_cfdis, paquetes, mensaje
