"""Compara service.py viejo vs nuevo y detecta cambios breaking."""
from __future__ import annotations

import ast
import re
from pathlib import Path


class SkillBreakingDetectorService:

    def ejecutar(self, context: dict) -> dict:
        old_code   = (context.get("old_code") or "").strip()
        new_code   = (context.get("new_code") or "").strip()
        skill_name = (context.get("skill_name") or "desconocido").strip()

        # También acepta rutas de archivo
        if not old_code and context.get("old_path"):
            p = Path(context["old_path"])
            if p.exists():
                old_code = p.read_text(encoding="utf-8")
        if not new_code and context.get("new_path"):
            p = Path(context["new_path"])
            if p.exists():
                new_code = p.read_text(encoding="utf-8")

        if not old_code:
            return {"ok": False, "error": "old_code o old_path requerido"}
        if not new_code:
            return {"ok": False, "error": "new_code o new_path requerido"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        old_info = self._analizar(old_code)
        new_info = self._analizar(new_code)
        cambios  = self._detectar_cambios(old_info, new_info)

        breaking = [c for c in cambios if c["severidad"] == "breaking"]
        warnings = [c for c in cambios if c["severidad"] == "warning"]

        safe = len(breaking) == 0
        return {
            "ok": True,
            "message": f"{'SIN BREAKING CHANGES' if safe else f'{len(breaking)} BREAKING CHANGES'} — {len(warnings)} warnings",
            "data": {
                "skill_name": skill_name,
                "safe": safe,
                "breaking_count": len(breaking),
                "warning_count":  len(warnings),
                "cambios": cambios,
                "resumen": {
                    "funciones_removidas":  [c["detalle"] for c in cambios if c["tipo"] == "funcion_removida"],
                    "firmas_cambiadas":     [c["detalle"] for c in cambios if c["tipo"] == "firma_cambiada"],
                    "retorno_cambiado":     [c["detalle"] for c in cambios if c["tipo"] == "retorno_cambiado"],
                    "env_vars_nuevas":      [c["detalle"] for c in cambios if c["tipo"] == "env_nueva"],
                },
            },
        }

    # --- análisis ---

    def _analizar(self, code: str) -> dict:
        info = {
            "funciones":  {},
            "env_vars":   set(),
            "imports":    set(),
            "tiene_dry_run": bool(re.search(r"dry_run", code, re.I)),
            "retorna_ok": bool(re.search(r"['\"]ok['\"]", code)),
        }
        # parse AST para funciones y firmas
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in node.args.args]
                    info["funciones"][node.name] = args
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "getenv":
                        for a in node.args:
                            if isinstance(a, ast.Constant):
                                info["env_vars"].add(a.value)
        except SyntaxError:
            # fallback regex
            for m in re.finditer(r"def (\w+)\(([^)]*)\)", code):
                params = [p.strip().split(":")[0].split("=")[0].strip() for p in m.group(2).split(",") if p.strip()]
                info["funciones"][m.group(1)] = params
            for m in re.finditer(r'os\.getenv\(["\'](\w+)["\']', code):
                info["env_vars"].add(m.group(1))
        return info

    def _detectar_cambios(self, old: dict, new: dict) -> list:
        cambios = []

        # funciones removidas
        for fn in old["funciones"]:
            if fn not in new["funciones"]:
                cambios.append({"tipo": "funcion_removida", "severidad": "breaking",
                                 "detalle": f"función '{fn}' eliminada"})

        # firmas cambiadas en funciones públicas (no privadas _)
        for fn, old_args in old["funciones"].items():
            if fn in new["funciones"]:
                new_args = new["funciones"][fn]
                if old_args != new_args:
                    sev = "breaking" if not fn.startswith("_") else "warning"
                    cambios.append({"tipo": "firma_cambiada", "severidad": sev,
                                     "detalle": f"'{fn}': {old_args} → {new_args}"})

        # dry_run removido
        if old["tiene_dry_run"] and not new["tiene_dry_run"]:
            cambios.append({"tipo": "retorno_cambiado", "severidad": "breaking",
                             "detalle": "dry_run eliminado — skills que dependían de él fallarán"})

        # retorno ok removido
        if old["retorna_ok"] and not new["retorna_ok"]:
            cambios.append({"tipo": "retorno_cambiado", "severidad": "breaking",
                             "detalle": "campo 'ok' eliminado del retorno"})

        # env vars nuevas requeridas
        nuevas_env = new["env_vars"] - old["env_vars"]
        for env in nuevas_env:
            cambios.append({"tipo": "env_nueva", "severidad": "warning",
                             "detalle": f"nueva variable de entorno requerida: {env}"})

        return cambios
