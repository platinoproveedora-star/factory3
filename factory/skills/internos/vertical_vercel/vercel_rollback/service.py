from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import _vercel_client as vc


class VercelRollbackService:
    def ejecutar(self, ctx: dict) -> dict:
        project_id    = ctx.get("project_id") or ctx.get("name", "")
        deployment_id = ctx.get("deployment_id", "")

        if not project_id:
            return {"ok": False, "error": "project_id o name requerido"}

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
