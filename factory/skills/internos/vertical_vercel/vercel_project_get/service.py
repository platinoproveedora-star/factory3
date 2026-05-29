from __future__ import annotations
import importlib.util as _ilu
from pathlib import Path

_VC_PATH = Path(__file__).parent.parent / "_vercel_client.py"
_vc_spec = _ilu.spec_from_file_location("_vercel_client", _VC_PATH)
vc       = _ilu.module_from_spec(_vc_spec)
_vc_spec.loader.exec_module(vc)


class VercelProjectGetService:
    def ejecutar(self, ctx: dict) -> dict:
        name = ctx.get("name") or ctx.get("project_id", "")
        if not name:
            return {"ok": False, "error": "name o project_id requerido"}

        r = vc.get(f"/v9/projects/{name}")
        if not r["ok"]:
            return r
        project = r["data"]

        # Últimos 5 deploys
        rd = vc.get(f"/v6/deployments", qs={"projectId": project.get("id"), "limit": 5})
        deployments = []
        if rd["ok"]:
            for d in rd["data"].get("deployments", []):
                deployments.append({
                    "deployment_id": d.get("uid"),
                    "url":           f"https://{d.get('url')}",
                    "state":         d.get("readyState"),
                    "created_at":    d.get("createdAt"),
                    "target":        d.get("target", "preview"),
                })

        return {"ok": True, "data": {
            "project": {
                "project_id": project.get("id"),
                "name":       project.get("name"),
                "framework":  project.get("framework"),
                "url":        f"https://{project['name']}.vercel.app",
                "repo":       (project.get("link") or {}).get("repo"),
            },
            "deployments": deployments,
        }}
