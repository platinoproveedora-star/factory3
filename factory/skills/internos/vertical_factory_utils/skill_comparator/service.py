"""Service for skill_comparator — detects duplicates and overlaps between a skill box and the registry."""

from __future__ import annotations

import json
import re
from pathlib import Path

_STOP_WORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "y", "o", "en",
    "a", "para", "con", "por", "que", "se", "al", "su", "sus", "si",
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "is",
}

_ACCION_ORDEN = {"duplicado_exacto": 0, "solapamiento": 1, "nuevo": 2}


class SkillComparatorService:

    def ejecutar(self, context: dict) -> dict:
        box_path = context.get("box_path")
        if not box_path:
            return {"ok": False, "error": "box_path es requerido"}

        box_dir = Path(box_path)
        if not box_dir.is_dir():
            return {"ok": False, "error": f"box_path no existe o no es carpeta: {box_path}"}

        base_dir = Path(context.get("base_dir", "factory"))
        threshold = float(context.get("threshold", 0.2))

        registry = self._cargar_registry(base_dir / "skills" / "registry.json")
        box_skills = self._cargar_box(box_dir)

        if not box_skills:
            return {"ok": False, "error": f"no se encontraron skills validos en: {box_path}"}

        tabla = [
            self._comparar_skill(nombre, info, registry, threshold)
            for nombre, info in sorted(box_skills.items())
        ]
        tabla.sort(key=lambda r: _ACCION_ORDEN.get(r["accion"], 3))

        resumen = {
            "duplicados_exactos": sum(1 for r in tabla if r["accion"] == "duplicado_exacto"),
            "solapamientos": sum(1 for r in tabla if r["accion"] == "solapamiento"),
            "nuevos": sum(1 for r in tabla if r["accion"] == "nuevo"),
            "total_en_caja": len(tabla),
            "total_en_registry": len(registry),
        }

        return {"ok": True, "data": {"tabla": tabla, "resumen": resumen}}

    # --- carga ---

    def _cargar_registry(self, registry_path: Path) -> dict:
        if not registry_path.exists():
            return {}
        for encoding in ("utf-8", "utf-8-sig", "utf-16"):
            try:
                raw = registry_path.read_text(encoding=encoding).strip()
                return json.loads(raw) if raw else {}
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
        return {}

    def _cargar_box(self, box_dir: Path) -> dict[str, dict]:
        skills: dict[str, dict] = {}
        for candidate in sorted(box_dir.iterdir()):
            if not candidate.is_dir():
                continue
            info = self._leer_skill_info(candidate)
            if info:
                skills[candidate.name] = info
        return skills

    def _leer_skill_info(self, skill_dir: Path) -> dict | None:
        manifest_path = skill_dir / "manifest.json"
        skill_md_path = skill_dir / "SKILL.md"

        if not manifest_path.exists() and not skill_md_path.exists():
            return None

        info: dict = {"path": str(skill_dir), "descripcion": "", "vertical": "", "version": ""}

        if manifest_path.exists():
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                info["descripcion"] = data.get("description", "")
                info["vertical"] = data.get("vertical", "")
                info["version"] = data.get("version", "")
            except (OSError, json.JSONDecodeError):
                pass

        if skill_md_path.exists():
            try:
                info["skill_md_preview"] = skill_md_path.read_text(encoding="utf-8")[:400]
            except OSError:
                pass

        return info

    # --- comparacion ---

    def _comparar_skill(self, nombre: str, info: dict, registry: dict, threshold: float) -> dict:
        desc_caja = info.get("descripcion", "")

        if nombre in registry:
            existing = registry[nombre]
            return {
                "skill_caja": nombre,
                "descripcion_caja": desc_caja,
                "vertical_caja": info.get("vertical", ""),
                "match_exacto": True,
                "skills_similares": [{
                    "nombre": nombre,
                    "descripcion": existing.get("descripcion", ""),
                    "vertical": existing.get("vertical", ""),
                    "similitud": 1.0,
                }],
                "similitud_max": 1.0,
                "accion": "duplicado_exacto",
            }

        similares = []
        for reg_nombre, reg_entry in registry.items():
            sim = self._jaccard(desc_caja, reg_entry.get("descripcion", ""))
            if sim >= threshold:
                similares.append({
                    "nombre": reg_nombre,
                    "descripcion": reg_entry.get("descripcion", ""),
                    "vertical": reg_entry.get("vertical", ""),
                    "similitud": round(sim, 3),
                })

        similares.sort(key=lambda x: x["similitud"], reverse=True)
        similares = similares[:5]

        similitud_max = similares[0]["similitud"] if similares else 0.0
        accion = "solapamiento" if similares else "nuevo"

        return {
            "skill_caja": nombre,
            "descripcion_caja": desc_caja,
            "vertical_caja": info.get("vertical", ""),
            "match_exacto": False,
            "skills_similares": similares,
            "similitud_max": similitud_max,
            "accion": accion,
        }

    # --- texto ---

    def _tokenizar(self, texto: str) -> set[str]:
        tokens = re.findall(r"[a-záéíóúñA-ZÁÉÍÓÚÑA-Za-z]+", texto.lower())
        return {t for t in tokens if t not in _STOP_WORDS and len(t) > 2}

    def _jaccard(self, a: str, b: str) -> float:
        ta = self._tokenizar(a)
        tb = self._tokenizar(b)
        if not ta and not tb:
            return 0.0
        union = ta | tb
        if not union:
            return 0.0
        return len(ta & tb) / len(union)
