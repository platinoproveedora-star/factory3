from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import _vercel_client as vc


class VercelEnvSyncService:
    def ejecutar(self, ctx: dict) -> dict:
        project_id = ctx.get("project_id") or ctx.get("name", "")
        envs       = ctx.get("envs", {})
        target     = ctx.get("target", ["production", "preview"])

        if not project_id:
            return {"ok": False, "error": "project_id o name requerido"}
        if not envs:
            return {"ok": False, "error": "envs dict requerido (KEY: VALUE)"}
        if isinstance(target, str):
            target = [target]

        # Obtener envs actuales para saber cuáles hacer PATCH vs POST
        r_existing = vc.get(f"/v9/projects/{project_id}/env")
        existing: dict = {}  # key → env_id
        if r_existing["ok"]:
            for e in r_existing["data"].get("envs", []):
                existing[e["key"]] = e["id"]

        synced  = []
        errors  = []

        for key, value in envs.items():
            body = {
                "key":    key,
                "value":  str(value),
                "type":   "encrypted",
                "target": target,
            }
            if key in existing:
                # Actualizar
                r = vc.patch(f"/v9/projects/{project_id}/env/{existing[key]}", body=body)
            else:
                # Crear
                r = vc.post(f"/v10/projects/{project_id}/env", body=body)

            if r["ok"]:
                synced.append(key)
            else:
                errors.append(f"{key}: {r.get('error')}")

        if errors:
            return {"ok": False, "error": "; ".join(errors), "data": {"synced": synced}}

        return {"ok": True, "data": {"synced": len(synced), "vars": synced}}
