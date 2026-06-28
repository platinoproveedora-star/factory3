"""Parsea un XML CFDI 3.3 / 4.0 y retorna dict estructurado."""
from __future__ import annotations

_NS33 = "http://www.sat.gob.mx/cfd/3"
_NS40 = "http://www.sat.gob.mx/cfd/4"
_NS_TFD = "http://www.sat.gob.mx/TimbreFiscalDigital"


class SatCfdiParserService:

    def ejecutar(self, context: dict) -> dict:
        xml_str = context.get("xml") or context.get("xml_str") or ""
        xmls    = context.get("xmls") or []

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"cfdis": []}}

        if xml_str:
            try:
                parsed = self._parsear(xml_str)
                return {"ok": True, "message": "1 CFDI parseado", "data": {"cfdis": [parsed]}}
            except Exception as e:
                return {"ok": False, "error": f"Error parseando CFDI: {e}"}

        if xmls:
            resultados = []
            errores    = 0
            for x in xmls:
                try:
                    resultados.append(self._parsear(x))
                except Exception:
                    errores += 1
            return {
                "ok":      errores == 0,
                "message": f"{len(resultados)} parseados, {errores} errores",
                "data":    {"cfdis": resultados, "errores": errores},
            }

        return {"ok": False, "error": "Se requiere 'xml' o 'xmls' en context"}

    def _parsear(self, xml_str: str) -> dict:
        from lxml import etree
        xml_bytes = xml_str.lstrip("\ufeff").encode("utf-8") if isinstance(xml_str, str) else xml_str
        root = etree.fromstring(xml_bytes)
        ns   = root.nsmap.get(None) or _NS40

        def a(attr):
            return root.get(attr) or root.get(attr.lower()) or ""

        emisor   = root.find(f"{{{ns}}}Emisor")
        receptor = root.find(f"{{{ns}}}Receptor")
        tfd      = root.find(f".//{{{_NS_TFD}}}TimbreFiscalDigital")

        conceptos = []
        for c in root.findall(f".//{{{ns}}}Concepto"):
            conceptos.append({
                "descripcion":    c.get("Descripcion", ""),
                "cantidad":       c.get("Cantidad", ""),
                "valor_unitario": c.get("ValorUnitario", ""),
                "importe":        c.get("Importe", ""),
                "clave_prod_serv": c.get("ClaveProdServ", ""),
            })

        impuestos = {
            "iva_trasladado": 0.0,
            "iva_retenido": 0.0,
            "isr_retenido": 0.0,
            "total_trasladados": 0.0,
            "total_retenidos": 0.0,
        }
        for traslado in root.findall(f".//{{{ns}}}Traslado"):
            importe = self._to_float(traslado.get("Importe", "0"))
            impuestos["total_trasladados"] += importe
            if traslado.get("Impuesto") == "002":
                impuestos["iva_trasladado"] += importe
        for retencion in root.findall(f".//{{{ns}}}Retencion"):
            importe = self._to_float(retencion.get("Importe", "0"))
            impuestos["total_retenidos"] += importe
            if retencion.get("Impuesto") == "002":
                impuestos["iva_retenido"] += importe
            if retencion.get("Impuesto") == "001":
                impuestos["isr_retenido"] += importe

        return {
            "uuid":             tfd.get("UUID", "") if tfd is not None else "",
            "version":          a("Version"),
            "tipo_comprobante": a("TipoDeComprobante"),
            "fecha_emision":    a("Fecha"),
            "fecha_timbrado":   tfd.get("FechaTimbrado", "") if tfd is not None else "",
            "serie":            a("Serie"),
            "folio":            a("Folio"),
            "subtotal":         a("SubTotal"),
            "descuento":        a("Descuento") or "0",
            "total":            a("Total"),
            "moneda":           a("Moneda") or "MXN",
            "tipo_cambio":      a("TipoCambio") or "1",
            "metodo_pago":      a("MetodoPago"),
            "forma_pago":       a("FormaPago"),
            "uso_cfdi":         receptor.get("UsoCFDI", "") if receptor is not None else "",
            "rfc_emisor":       emisor.get("Rfc", "")    if emisor   is not None else "",
            "nombre_emisor":    emisor.get("Nombre", "")  if emisor   is not None else "",
            "rfc_receptor":     receptor.get("Rfc", "")   if receptor is not None else "",
            "nombre_receptor":  receptor.get("Nombre", "") if receptor is not None else "",
            "conceptos":        conceptos,
            "impuestos":        impuestos,
            "iva":              round(impuestos["iva_trasladado"] - impuestos["iva_retenido"], 2),
            "xml_raw":          xml_str if isinstance(xml_str, str) else xml_str.decode("utf-8"),
        }

    def _to_float(self, value: str) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
