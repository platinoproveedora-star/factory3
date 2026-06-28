"""Paso 1 sync granular: sat_auth + sat_cfdi_solicitud → id_solicitud. Sin polling bloqueante."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

_VERTICAL_SAT = Path(__file__).parent.parent.parent / "vertical_sat"


class Conta4allSyncStartService:

    def ejecutar(self, context: dict) -> dict:
        rfc          = (context.get("rfc") or os.getenv("SAT_RFC", "")).strip().upper()
        cer_b64      = context.get("cer_b64") or os.getenv("SAT_EFIRMA_CER_B64", "")
        key_b64      = context.get("key_b64") or os.getenv("SAT_EFIRMA_KEY_B64", "")
        key_pwd      = context.get("key_password") or os.getenv("SAT_EFIRMA_PASSWORD", "")
        fecha_inicio = (context.get("fecha_inicio") or "").strip()
        fecha_fin    = (context.get("fecha_fin") or "").strip()
        tipo         = context.get("tipo", "E")
        tipo_sol     = context.get("tipo_solicitud", "CFDI")
        tipo_comp    = context.get("tipo_comprobante", "")
        rfc_cp       = context.get("rfc_contraparte", "")

        if context.get("dry_run"):
            return {"ok": True, "message": "dry_run", "data": {"id_solicitud": "DRY-RUN"}}

        if not all([rfc, cer_b64, key_b64, key_pwd, fecha_inicio, fecha_fin]):
            return {"ok": False,
                    "error": "Faltan: rfc, cer_b64, key_b64, key_password, fecha_inicio, fecha_fin"}

        creds = {"rfc": rfc, "cer_b64": cer_b64, "key_b64": key_b64, "key_password": key_pwd}

        r1 = self._run_sat("sat_auth", {**creds, "dry_run": False})
        if not r1.get("ok"):
            return {"ok": False, "error": f"sat_auth: {r1.get('error', '')}",
                    "data": {"paso": "sat_auth"}}
        token = r1["data"]["token"]

        r2 = self._run_sat("sat_cfdi_solicitud", {
            **creds,
            "token":            token,
            "fecha_inicio":     fecha_inicio,
            "fecha_fin":        fecha_fin,
            "tipo":             tipo,
            "tipo_comprobante": tipo_comp,
            "tipo_solicitud":   tipo_sol,
            "rfc_contraparte":  rfc_cp,
            "dry_run":          False,
        })
        if not r2.get("ok"):
            return {"ok": False, "error": f"sat_cfdi_solicitud: {r2.get('error', '')}",
                    "data": {"paso": "sat_cfdi_solicitud"}}

        id_solicitud = r2["data"]["id_solicitud"]
        return {
            "ok":      True,
            "message": f"Solicitud creada: {id_solicitud}",
            "data": {
                "id_solicitud": id_solicitud,
                "tipo":         tipo,
                "fecha_inicio": fecha_inicio,
                "fecha_fin":    fecha_fin,
            },
        }

    def _run_sat(self, skill_name: str, ctx: dict) -> dict:
        skill_path  = _VERTICAL_SAT / skill_name
        entrypoint  = skill_path / "skill.py"
        if not entrypoint.exists():
            return {"ok": False, "error": f"sat skill no encontrado: {skill_name}"}
        module_name = f"_sat_{skill_name}"
        spec        = importlib.util.spec_from_file_location(module_name, entrypoint)
        if not spec or not spec.loader:
            return {"ok": False, "error": f"error cargando: {skill_name}"}
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(skill_path))
        for k in [k for k in sys.modules if k in ("service", "skill")]:
            del sys.modules[k]
        try:
            spec.loader.exec_module(module)
            return module.run(ctx)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            if sys.path and sys.path[0] == str(skill_path):
                sys.path.pop(0)
