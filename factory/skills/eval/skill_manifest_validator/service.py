"""Valida que todos los manifests tengan campos requeridos con valores correctos."""
from __future__ import annotations

import json
from pathlib import Path

_SKILLS_ROOT = Path(__file__).parent.parent.parent  # factory/skills/
_FOLDERS     = ["internos", "meta", "eval"]

_RULES = [
    ("name",        str,  True,  "debe ser string no vacío"),
    ("type",        str,  True,  "debe ser string no vacío"),
    ("kind",        str,  True,  "debe ser 'executable' o 'data'"),
    ("entrypoint",  str,  True,  "debe apuntar a skill.py"),
    ("description", str,  True,  "debe tener descripción"),
    ("version",     str,  False, "recomendado: '0.1.0'"),
    ("requires_env",list, False, "recomendado: lista (puede ser vacía)"),
]

_VALID_KINDS = {"executable", "data"}


class SkillManifestValidatorService:

    def ejecutar(self, context: dict) -> dict:
        skill_name = context.get("skill_name")
        folders    = context.get("folders") or _FOLDERS

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        if skill_name:
            resultados = [self._validar_uno(skill_name, folders)]
        else:
            resultados = self._validar_todos(folders)

        validos   = sum(1 for r in resultados if r["valido"])
        invalidos = len(resultados) - validos

        return {
            "ok": invalidos == 0,
            "message": f"{validos} validos · {invalidos} con errores de {len(resultados)} manifests",
            "data": {
                "total":    len(resultados),
                "validos":  validos,
                "invalidos": invalidos,
                "resultados": resultados,
            },
        }

    def _validar_todos(self, folders: list) -> list:
        resultados = []
        for folder in folders:
            folder_path = _SKILLS_ROOT / folder
            if not folder_path.exists():
                continue
            for skill_dir in sorted(folder_path.iterdir()):
                if not skill_dir.is_dir() or skill_dir.name.startswith(("_", ".")):
                    continue
                m_path = skill_dir / "manifest.json"
                if m_path.exists():
                    resultados.append(self._validar_manifest(skill_dir.name, folder, m_path))
                else:
                    resultados.append({
                        "nombre": skill_dir.name, "folder": folder,
                        "valido": False, "errores": ["manifest.json no existe"], "warnings": [],
                    })
        return resultados

    def _validar_uno(self, skill_name: str, folders: list) -> dict:
        for folder in folders:
            m_path = _SKILLS_ROOT / folder / skill_name / "manifest.json"
            if m_path.exists():
                return self._validar_manifest(skill_name, folder, m_path)
        return {"nombre": skill_name, "folder": "?", "valido": False,
                "errores": ["skill no encontrado en ninguna carpeta"], "warnings": []}

    def _validar_manifest(self, nombre: str, folder: str, path: Path) -> dict:
        errores  = []
        warnings = []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            return {"nombre": nombre, "folder": folder, "valido": False,
                    "errores": [f"JSON inválido: {e}"], "warnings": []}

        for field, ftype, required, hint in _RULES:
            val = data.get(field)
            if val is None:
                if required:
                    errores.append(f"falta campo requerido '{field}' — {hint}")
                else:
                    warnings.append(f"campo opcional ausente '{field}' — {hint}")
            elif not isinstance(val, ftype):
                errores.append(f"campo '{field}' tipo incorrecto: esperado {ftype.__name__}")
            elif ftype == str and not val.strip():
                if required:
                    errores.append(f"campo '{field}' está vacío")

        kind = data.get("kind", "")
        if kind and kind not in _VALID_KINDS:
            errores.append(f"kind='{kind}' no válido, debe ser: {_VALID_KINDS}")

        name_in_manifest = data.get("name", "")
        if name_in_manifest and name_in_manifest != nombre:
            warnings.append(f"name en manifest ('{name_in_manifest}') != nombre de carpeta ('{nombre}')")

        return {
            "nombre":   nombre,
            "folder":   folder,
            "valido":   len(errores) == 0,
            "errores":  errores,
            "warnings": warnings,
        }
