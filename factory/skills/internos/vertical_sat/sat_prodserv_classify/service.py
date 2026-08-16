"""Clasificador generico basado en catalogos oficiales del SAT.

No existe un campo oficial "es mercancia / es servicio" en ningun catalogo
del SAT. Esto combina dos catalogos reales para inferirlo:

1. c_UsoCFDI — catalogo cerrado que declara el RECEPTOR de un CFDI (para que
   va a usar la factura). Es la senal mas confiable para clasificar
   documentos RECIBIDOS (egresos), porque nosotros mismos controlamos que
   UsoCFDI le damos al proveedor.
2. Segmento (primeros 2 digitos) de c_ClaveProdServ (Catalogo de Productos y
   Servicios, base UNSPSC) — util como respaldo, y es la unica senal
   disponible para documentos EMITIDOS (ingresos), donde el UsoCFDI lo
   declara el cliente para sus propios fines, no dice si nosotros vendimos
   mercancia o un servicio.
"""
from __future__ import annotations

_USO_CFDI_GROUP = {
    "G01": "mercancia",
    "G02": "devolucion_descuento",
    "G03": "gasto_general",
    "I01": "activo_fijo", "I02": "activo_fijo", "I03": "activo_fijo",
    "I04": "activo_fijo", "I05": "activo_fijo", "I06": "activo_fijo",
    "I07": "activo_fijo", "I08": "activo_fijo",
    "D01": "deduccion_personal", "D02": "deduccion_personal", "D03": "deduccion_personal",
    "D04": "deduccion_personal", "D05": "deduccion_personal", "D06": "deduccion_personal",
    "D07": "deduccion_personal", "D08": "deduccion_personal", "D09": "deduccion_personal",
    "D10": "deduccion_personal",
    "S01": "sin_efecto_fiscal",
    "CP01": "complemento_pago",
    "CN01": "nomina",
}

# Segmento (2 digitos) de c_ClaveProdServ -> grupo. 10-60 son divisiones de
# bienes/materiales/equipo; 70-95 son divisiones de servicios. Heuristico,
# no un campo oficial — por eso siempre puede sobreescribirse manualmente
# en el producto (classification_source='manual').
_MERCANCIA_SEGMENTS = {f"{n:02d}" for n in list(range(10, 61))}
_SERVICIO_SEGMENTS = {f"{n:02d}" for n in list(range(70, 96))}

_GENERIC_CLAVE = "01010101"  # "No existe en el catalogo" — siempre a revision


class SatProdservClassifyService:
    def ejecutar(self, context: dict) -> dict:
        uso_cfdi = str(context.get("uso_cfdi") or "").strip().upper()
        clave_prod_serv = str(context.get("clave_prod_serv") or "").strip()

        if uso_cfdi and uso_cfdi in _USO_CFDI_GROUP:
            return {
                "ok": True,
                "data": {
                    "classification_group": _USO_CFDI_GROUP[uso_cfdi],
                    "source": "auto_uso_cfdi",
                    "signal": uso_cfdi,
                },
            }

        if clave_prod_serv and clave_prod_serv != _GENERIC_CLAVE and len(clave_prod_serv) >= 2:
            segment = clave_prod_serv[:2]
            if segment in _MERCANCIA_SEGMENTS:
                return {"ok": True, "data": {"classification_group": "mercancia", "source": "auto_catalog", "signal": segment}}
            if segment in _SERVICIO_SEGMENTS:
                return {"ok": True, "data": {"classification_group": "servicio", "source": "auto_catalog", "signal": segment}}

        return {"ok": True, "data": {"classification_group": "pending_review", "source": "pending_review", "signal": uso_cfdi or clave_prod_serv}}
