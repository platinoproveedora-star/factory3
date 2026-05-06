"""Service for rh_duplicate_detector - detects duplicate candidates."""

from __future__ import annotations

from factory.engine import SupabaseClient


class RhDuplicateDetectorService:

    def ejecutar(self, context: dict) -> dict:
        candidato_id = context.get("candidato_id", "").strip()
        vacante_id   = context.get("vacante_id", "").strip()
        telefono     = context.get("telefono", "").strip()
        email        = context.get("email", "").strip()
        canal_user_id = context.get("canal_user_id", "").strip()

        if not candidato_id:
            return {"ok": False, "error": "candidato_id es requerido"}
        if not vacante_id:
            return {"ok": False, "error": "vacante_id es requerido"}
        if not any([telefono, email, canal_user_id]):
            return {"ok": False, "error": "se requiere al menos uno: telefono, email o canal_user_id"}

        db = SupabaseClient(context)

        checks = []
        if telefono:
            checks.append(("telefono", telefono))
        if email:
            checks.append(("email", email))
        if canal_user_id:
            checks.append(("canal_user_id", canal_user_id))

        for campo, valor in checks:
            resultado = self._buscar(db, campo, valor, candidato_id, vacante_id)
            if not resultado.get("ok"):
                return resultado
            existente = resultado.get("data")
            if existente:
                return {
                    "ok": True,
                    "data": {
                        "es_duplicado": True,
                        "candidato_existente_id": existente["id"],
                        "campo_coincidencia": campo,
                        "valor_coincidencia": valor,
                    },
                }

        return {
            "ok": True,
            "data": {
                "es_duplicado": False,
                "candidato_existente_id": None,
                "campo_coincidencia": None,
                "valor_coincidencia": None,
            },
        }

    def _buscar(self, db: SupabaseClient, campo: str, valor: str, excluir_id: str, vacante_id: str) -> dict:
        result = db.rest_select(
            "candidatos",
            filters={campo: valor, "vacante_id": vacante_id},
            select="id,nombre,canal",
            limit=1,
        )
        if not result.get("ok"):
            return result
        rows = [r for r in (result.get("data") or []) if r.get("id") != excluir_id]
        return {"ok": True, "data": rows[0] if rows else None}
