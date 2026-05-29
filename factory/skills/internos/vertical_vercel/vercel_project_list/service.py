from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import _vercel_client as vc


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
