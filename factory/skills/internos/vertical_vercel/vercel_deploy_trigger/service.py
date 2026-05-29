from __future__ import annotations
import importlib.util as _ilu
from pathlib import Path

_VC_PATH = Path(__file__).parent.parent / "_vercel_client.py"
_vc_spec = _ilu.spec_from_file_location("_vercel_client", _VC_PATH)
vc       = _ilu.module_from_spec(_vc_spec)
_vc_spec.loader.exec_module(vc)


class VercelDeployTriggerService:
    def ejecutar(self, ctx: dict) -> dict:
        project_id = ctx.get("project_id") or ctx.get("name", "")
        target     = ctx.get("target", "production")

        dry_run = ctx.get("dry_run", True)

        if not project_id:
            return {"ok": False, "error": "project_id o name requerido"}

        if dry_run:
            return {"ok": True, "data": {
                "dry_run": True,
                "preview": {"project_id": project_id, "target": target},
            }}

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
