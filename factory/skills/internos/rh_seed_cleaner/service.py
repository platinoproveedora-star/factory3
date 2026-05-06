"""Service for rh_seed_cleaner - deletes all records for a seed_label in FK order."""

from __future__ import annotations

from factory.engine import SupabaseClient

# Orden de borrado respetando FK (de hijos a padres)
_DELETE_ORDER = [
    "alertas",
    "eventos_historial",
    "pipeline",
    "scores",
    "respuestas",
    "conversaciones",
    "candidatos",
    "cuestionarios",
    "vacantes",
]


class RhSeedCleanerService:

    def ejecutar(self, context: dict) -> dict:
        seed_label = context.get("seed_label", "").strip()
        empresa_id = context.get("empresa_id", "").strip()

        if not seed_label:
            return {"ok": False, "error": "seed_label es requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id es requerido como confirmacion de seguridad"}

        # Forzar prefijo seed_ como capa de seguridad
        if not empresa_id.startswith("seed_"):
            empresa_id = f"seed_{empresa_id}"

        db = SupabaseClient(context)

        # Leer todos los registros del seed
        seeds_r = db.rest_select(
            "test_seeds",
            filters={"seed_label": seed_label, "empresa_id": empresa_id},
            select="id,tabla,registro_id",
        )
        if not seeds_r.get("ok"):
            return seeds_r

        seeds = seeds_r.get("data") or []
        if not seeds:
            return {"ok": True, "message": f"no se encontraron registros para seed '{seed_label}'", "data": {"borrados": {}}}

        # Agrupar por tabla
        por_tabla: dict[str, list] = {}
        seed_ids: list[str] = []
        for s in seeds:
            tabla = s["tabla"]
            por_tabla.setdefault(tabla, []).append(s["registro_id"])
            seed_ids.append(s["id"])

        if context.get("dry_run", True):
            preview = {t: len(ids) for t, ids in por_tabla.items()}
            preview["test_seeds"] = len(seeds)
            return {
                "ok": True,
                "message": "dry_run: nada borrado",
                "data": {"seed_label": seed_label, "empresa_id": empresa_id, "preview_borrado": preview},
            }

        borrados: dict[str, int] = {}

        # Borrar en orden FK
        for tabla in _DELETE_ORDER:
            ids = por_tabla.get(tabla, [])
            if not ids:
                continue
            count = 0
            for registro_id in ids:
                r = db.rest_delete(tabla, filters={"id": registro_id})
                if r.get("ok"):
                    count += 1
            if count:
                borrados[tabla] = count

        # Borrar registros de test_seeds usando SQL para borrar por seed_label + empresa_id
        from factory.engine import SupabaseClient as SC
        for seed_id in seed_ids:
            db.rest_delete("test_seeds", filters={"id": seed_id})
        borrados["test_seeds"] = len(seed_ids)

        total = sum(borrados.values())
        return {
            "ok": True,
            "message": f"seed '{seed_label}' eliminado — {total} registros borrados",
            "data": {
                "seed_label": seed_label,
                "empresa_id": empresa_id,
                "borrados":   borrados,
            },
        }
