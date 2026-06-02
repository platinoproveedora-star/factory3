from __future__ import annotations


PREFIXES = {
    "kardex": "KAR",
    "compra": "COM",
    "remision": "REM",
    "ajuste": "AJU",
    "devolucion": "DEV",
    "producto": "PROD",
    "party": "PTY",
}


class ErpInventoryDocumentFolioService:
    def ejecutar(self, context: dict) -> dict:
        folio_type = str(context.get("folio_type") or context.get("source_type") or "kardex").strip()
        prefix = str(context.get("prefix") or PREFIXES.get(folio_type, "KAR")).strip().upper()
        if context.get("next_number") is not None:
            next_number = int(context.get("next_number"))
        else:
            next_number = int(context.get("current_number") or 0) + 1
        digits = int(context.get("digits") or 5)
        folio = f"{prefix}-{next_number:0{digits}d}"
        return {"ok": True, "data": {"folio": folio, "prefix": prefix, "number": next_number, "digits": digits}}
