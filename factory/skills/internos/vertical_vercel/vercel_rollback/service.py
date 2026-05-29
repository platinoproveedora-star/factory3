from __future__ import annotations
import importlib.util as _ilu
from pathlib import Path

_VC_PATH = Path(__file__).parent.parent / "_vercel_client.py"
_vc_spec = _ilu.spec_from_file_location("_vercel_client", _VC_PATH)
vc       = _ilu.module_from_spec(_vc_spec)
_vc_spec.loader.exec_module(vc)


class VercelRollbackService:
    def ejecutar(self, ctx: dict) -> dict:
        project_id    = ctx.get("project_id") or ctx.get("name", "")
        deployment_id = ctx.get("deployment_id", "")

        dry_run = ctx.get("dry_run", True)

        if not project_id:
            return {"ok": False, "error": "project_id o name requerido"}

        if dry_run:
            return {"ok": True, "data": {
                "dry_run": True,
                "preview": {"project_id": project_id, "deployment_id": deployment_id or "penúltimo READY"},
            }}

        # Si no se especifica deployment_id, buscar el penúltimo deploy READY
        if not deployment_id:
            r_deps = vc.get(f"/v6/deployments", qs={"projectId": project_id, "limit": 5, "target": "production"})
            if not r_deps["ok"]:
                return r_deps
            deploys = [
                d for d in r_deps["data"].get("deployments", [])
                if d.get("readyState") == "READY"
            ]
            if len(deploys) < 2:
                return {"ok": False, "error": "No hay deploy anterior disponible para rollback"}
            deployment_id = deploys[1]["uid"]   # índice 0 = actual, 1 = anterior

        # Promover deploy anterior a producción
        r = vc.post(f"/v9/projects/{project_id}/rollback/{deployment_id}", body={})
        if not r["ok"]:
            # Fallback: algunos endpoints usan /promote
            r = vc.post(f"/v10/deployments/{deployment_id}/promote", body={"customEnvironmentId": None})
        if not r["ok"]:
            return r

        return {"ok": True, "data": {
            "rolled_back_to": deployment_id,
            "project_id":     project_id,
            "url":            f"https://{r['data'].get('url', '')}",
        }}
