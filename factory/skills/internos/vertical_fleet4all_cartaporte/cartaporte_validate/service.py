from __future__ import annotations

import re

_RFC_RE = re.compile(r"^[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}$")
_CLAVE_PROD_SERV_RE = re.compile(r"^\d{8}$")
_CLAVE_UNIDAD_RE = re.compile(r"^[A-Z0-9]{2,4}$")


class CartaporteValidateService:
    def ejecutar(self, context: dict) -> dict:
        draft = context.get("cartaporte") if isinstance(context.get("cartaporte"), dict) else None
        if not draft:
            return {"ok": False, "error": "missing_fields", "data": {"missing": ["cartaporte"]}}

        errors: list[str] = []
        errors.extend(self._check_structure(draft))
        errors.extend(self._check_rfc(context))
        errors.extend(self._check_mercancias(draft.get("mercancias") or []))

        if errors:
            return {"ok": False, "error": "invalid_cartaporte", "data": {"errors": errors}}
        return {"ok": True, "data": {"valid": True, "errors": []}}

    def _check_structure(self, draft: dict) -> list[str]:
        errors = []
        if draft.get("cfdi_type") not in ("traslado", "ingreso"):
            errors.append("cfdi_type debe ser traslado o ingreso")
        if not draft.get("origin") or not draft.get("destination"):
            errors.append("origin y destination requeridos")
        if not draft.get("unit_plate"):
            errors.append("unit_plate requerido")
        if not draft.get("driver_license"):
            errors.append("driver_license requerido")
        return errors

    def _check_rfc(self, context: dict) -> list[str]:
        rfc = str(context.get("rfc") or "").strip().upper()
        if rfc and not _RFC_RE.match(rfc):
            return [f"rfc con formato invalido: {rfc}"]
        return []

    def _check_mercancias(self, mercancias: list) -> list[str]:
        errors = []
        if not mercancias:
            errors.append("mercancias no puede estar vacio")
        for idx, m in enumerate(mercancias):
            try:
                peso = float(m.get("peso_kg") or 0)
            except (TypeError, ValueError):
                peso = 0
            if peso <= 0:
                errors.append(f"mercancias[{idx}].peso_kg debe ser mayor a 0")
            clave = str(m.get("clave_prod_serv") or "")
            if not _CLAVE_PROD_SERV_RE.match(clave):
                errors.append(f"mercancias[{idx}].clave_prod_serv debe ser 8 digitos SAT")
            clave_unidad = m.get("clave_unidad")
            if clave_unidad and not _CLAVE_UNIDAD_RE.match(str(clave_unidad).upper()):
                errors.append(f"mercancias[{idx}].clave_unidad con formato invalido")
        return errors
