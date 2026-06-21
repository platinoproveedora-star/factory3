from __future__ import annotations
import re


# ── patrones universales de tokens ──────────────────────────────────────────
_CLABE = re.compile(r'\b(\d{18})\b')
_RFC   = re.compile(r'\b([A-Z&]{3,4}\d{6}[A-Z0-9]{2,3})\b')
_HORA  = re.compile(r'\b(\d{2}:\d{2}:\d{2})\b')

# anclas de keywords (banco-agnósticas, estándar SPEI/Banxico)
_A = {
    'cve_rast':    re.compile(r'CVE\s*\.?\s*RAST(?:REO)?:\s*(\S+)', re.I),
    'referencia':  re.compile(r'REFERENCIA:\s*(\S+)', re.I),
    'cta_clabe':   re.compile(r'CTA/CLABE:\s*(\d{15,18})', re.I),
    'clabe':       re.compile(r'CLABE\s+(\d{15,18})', re.I),
    'del_cliente': re.compile(r'DEL\s+CLIENTE\s+(.+?)\s+DE\s+LA\s+CLABE', re.I),
    'benef':       re.compile(r'BENEF(?:ICIARIO)?:\s*(.+?)(?=\s*\(DATO|\s*,\s*[A-Z]{3}|\s*$)', re.I),
    'rfc':         re.compile(r'(?:CON\s+RFC|RFC:)\s*([A-Z&]{3,4}\d{6}[A-Z0-9]{2,3})', re.I),
    'bco':         re.compile(r'BCO:(\d{3,4})', re.I),
    'bco_nombre':  re.compile(r'BCO:\d{3,4}\s+([A-Z][A-Z\s]+?)(?=\s+HR\s+LIQ|\s+HORA|\s+DEL\s+CLIENTE)', re.I),
    'hora_liq':    re.compile(r'(?:HR|HORA)\s+LIQ\.?:\s*(\d{2}:\d{2}:\d{2})', re.I),
    'concepto':    re.compile(r'CONCEPTO:\s*(.+?)(?=\s+REFERENCIA:|\s+CVE|\s*$)', re.I),
    'cajero_de':   re.compile(r'en\s+el\s+cajero\s+de\s+(.+?)\s+a\s+las', re.I),
    'cajero_hora': re.compile(r'a\s+las\s+(\d{1,2}:\d{2})', re.I),
    'cajero_ref':  re.compile(r'-\s*(N\d+)', re.I),
    'cajero_mask': re.compile(r'\*{2}(\d{4})'),
    'cajero_tit':  re.compile(r'tarjeta\s+\*+\d+\s+de\s+(.+?)\s+en\s+el\s+cajero', re.I),
    'mes':         re.compile(r'MES\s+(\w+)', re.I),
    'ref_larga':   re.compile(r'(\d{7,12})\s+[\d,]+\.\d{2}'),
    'spei_clave':  re.compile(r'^(\S{10,30})\s+SPEI\s+RECIBIDO', re.I),
}

# tipos de movimiento detectables
_TIPOS = [
    ('SPEI_RECIBIDO',      re.compile(r'SPEI\s+RECIBIDO', re.I)),
    ('SPEI_ENVIADO',       re.compile(r'(?:COMPRA\s+)?ORDEN\s+DE\s+PAGO\s+SPEI', re.I)),
    ('EFECTIVO_DEPOSITO',  re.compile(r'DEPOSITO\s+EN\s+EFECTIVO', re.I)),
    ('TRANSFERENCIA_ENVIO',re.compile(r'TRANSFERENCIA.*?ENVIO', re.I)),
    ('IVA_SPEI',           re.compile(r'I\.V\.A\.\s+ORDEN\s+DE\s+PAGO\s+SPEI', re.I)),
    ('COMISION_RENTA',     re.compile(r'COMISION\s+POR\s+RENTA', re.I)),
    ('IVA_RENTA',          re.compile(r'IVA\s+POR\s+RENTA', re.I)),
]


def _clean_nombre(raw: str) -> str:
    """Elimina montos y espacios extra de un nombre capturado."""
    sin_montos = re.sub(r'\d[\d,\.]*', '', raw)
    return ' '.join(sin_montos.split())


class BankStatementFieldScannerService:
    """
    Scanner de tokens bancarios. Multi-banco, sin hardcodes.
    Recibe raw_text (str) y devuelve campos estructurados.
    Prioridad: ancla explícita > patrón por contexto > None.
    """

    def ejecutar(self, context: dict) -> dict:
        raw = str(context.get("raw_text") or "").strip()
        if not raw:
            return {"ok": False, "error": "raw_text requerido"}
        return {"ok": True, "data": self.scan(raw)}

    def scan(self, raw_text: str) -> dict:
        text = " ".join(raw_text.split())
        out: dict = {}
        meta: dict = {}

        # 1. tipo de movimiento
        tipo = self._detect_tipo(text)
        if tipo:
            meta["tipo_movimiento"] = tipo

        # 2. clave rastreo
        m = _A["cve_rast"].search(text)
        if m:
            out["clave_rastreo"] = m.group(1)
        elif tipo == "SPEI_RECIBIDO":
            m = _A["spei_clave"].search(text)
            if m:
                out["clave_rastreo"] = m.group(1)

        # 3. referencia
        m = _A["referencia"].search(text)
        if m:
            out["referencia"] = m.group(1)

        # 4. CLABE — rol según contexto
        m_cta = _A["cta_clabe"].search(text)      # CTA/CLABE: → destino explícito
        m_clabe = _A["clabe"].search(text)         # CLABE sola → origen si SPEI recibido

        if m_cta:
            out["cuenta_destino"] = m_cta.group(1)
        elif m_clabe:
            if tipo == "SPEI_RECIBIDO":
                out["cuenta_origen"] = m_clabe.group(1)
            elif tipo == "SPEI_ENVIADO":
                out["cuenta_destino"] = m_clabe.group(1)
            else:
                # sin contexto — CLABE sin ancla de rol: anotamos pero no asignamos
                meta["clabe_detectada"] = m_clabe.group(1)

        # 5. nombres
        m = _A["del_cliente"].search(text)
        if m:
            nombre = _clean_nombre(m.group(1))
            if len(nombre) >= 3:
                out["nombre_origen"] = nombre[:100]

        m = _A["benef"].search(text)
        if m:
            nombre = _clean_nombre(m.group(1))
            if len(nombre) >= 3:
                out["nombre_destino"] = nombre[:100]

        # efectivo: titular desde descripción
        if tipo == "EFECTIVO_DEPOSITO" and "nombre_destino" not in out:
            m = _A["cajero_tit"].search(text)
            if m:
                out["nombre_destino"] = m.group(1).strip()[:100]

        # 6. RFC
        m = _A["rfc"].search(text)
        if m:
            rfc_key = "rfc_origen" if tipo == "SPEI_RECIBIDO" else "rfc_destino"
            meta[rfc_key] = m.group(1)

        # 7. banco
        m = _A["bco"].search(text)
        if m:
            bco_key = "banco_origen_codigo" if tipo == "SPEI_RECIBIDO" else "banco_destino_codigo"
            meta[bco_key] = m.group(1)
            m2 = _A["bco_nombre"].search(text)
            if m2:
                nom_key = "banco_origen_nombre" if tipo == "SPEI_RECIBIDO" else "banco_destino_nombre"
                meta[nom_key] = m2.group(1).strip()

        # 8. hora liquidación
        m = _A["hora_liq"].search(text)
        if m:
            meta["hora_liquidacion"] = m.group(1)

        # 9. concepto libre
        m = _A["concepto"].search(text)
        if m:
            meta["concepto"] = m.group(1).strip()[:200]

        # 10. efectivo — campos adicionales
        if tipo == "EFECTIVO_DEPOSITO":
            m = _A["cajero_de"].search(text)
            if m:
                meta["sucursal"] = m.group(1).strip()[:200]
            m = _A["cajero_hora"].search(text)
            if m:
                meta["hora_liquidacion"] = m.group(1)
            m = _A["cajero_ref"].search(text)
            if m and "referencia" not in out:
                out["referencia"] = m.group(1)
            m = _A["cajero_mask"].search(text)
            if m:
                meta["cuenta_mask"] = f"**{m.group(1)}"

        # 11. comisión / IVA renta
        if tipo in ("COMISION_RENTA", "IVA_RENTA"):
            if "referencia" not in out:
                m = _A["ref_larga"].search(text)
                if m:
                    out["referencia"] = m.group(1)
            m = _A["mes"].search(text)
            if m:
                meta["periodo"] = f"MES {m.group(1).upper()}"

        out["metadata"] = meta
        return out

    def _detect_tipo(self, text: str) -> str | None:
        for tipo, pat in _TIPOS:
            if pat.search(text):
                return tipo
        return None
