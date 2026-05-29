from __future__ import annotations
import importlib.util as _ilu
from pathlib import Path

_VC_PATH = Path(__file__).parent.parent / "_vercel_client.py"
_vc_spec = _ilu.spec_from_file_location("_vercel_client", _VC_PATH)
vc       = _ilu.module_from_spec(_vc_spec)
_vc_spec.loader.exec_module(vc)


class VercelProjectListService:
    def ejecutar(self, ctx: dict) -> dict:
        limit  = int(ctx.get("limit", 20))
        search = ctx.get("search", "")

        qs: dict = {"limit": limit}
        if search:
            qs["search"] = search

        r = vc.get("/v9/projects", qs=qs)
        if not r["ok"]:
            return r

        raw = r["data"].get("projects", [])
        projects = [
            {
                "name":        p.get("name"),
                "project_id":  p.get("id"),
                "url":         f"https://{p['name']}.vercel.app",
                "state":       (p.get("latestDeployments") or [{}])[0].get("readyState", "—"),
                "last_deploy": (p.get("latestDeployments") or [{}])[0].get("createdAt"),
                "framework":   p.get("framework"),
            }
            for p in raw
        ]
        return {"ok": True, "data": {"projects": projects, "total": len(projects)}}
