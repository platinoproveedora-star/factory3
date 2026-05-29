from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import _vercel_client as vc


class VercelDeployTriggerService:
    def ejecutar(self, ctx: dict) -> dict:
        project_id = ctx.get("project_id") or ctx.get("name", "")
        target     = ctx.get("target", "production")

        if not project_id:
            return {"ok": False, "error": "project_id o name requerido"}

        # Obtener info del proyecto para saber el repo vinculado
        r_proj = vc.get(f"/v9/projects/{project_id}")
        if not r_proj["ok"]:
            return r_proj

        proj  = r_proj["data"]
        link  = proj.get("link") or {}
        repo  = link.get("repo", "")
        ref   = link.get("productionBranch", "main")

        body: dict = {
            "name":   proj.get("name"),
            "target": target,
        }

        if repo:
            body["gitSource"] = {
                "type": "github",
                "repo": repo,
                "ref":  ref,
            }

        r = vc.post("/v13/deployments", body=body)
        if not r["ok"]:
            return r

        d = r["data"]
        return {"ok": True, "data": {
            "deployment_id": d.get("id"),
            "url":           f"https://{d.get('url', '')}",
            "state":         d.get("readyState", "BUILDING"),
            "target":        target,
        }}
