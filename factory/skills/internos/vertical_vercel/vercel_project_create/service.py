from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import _vercel_client as vc


class VercelProjectCreateService:
    def ejecutar(self, ctx: dict) -> dict:
        name      = ctx.get("name", "").strip()
        repo      = ctx.get("repo", "").strip()       # "org/repo-name"
        framework = ctx.get("framework", "nextjs")
        root_dir  = ctx.get("root_dir", "")

        if not name:
            return {"ok": False, "error": "name requerido"}

        body: dict = {"name": name, "framework": framework}
        if root_dir:
            body["rootDirectory"] = root_dir

        # Vincular repo GitHub si se provee
        if repo:
            body["gitRepository"] = {
                "type": "github",
                "repo": repo,
            }

        r = vc.post("/v10/projects", body=body)
        if not r["ok"]:
            return r

        p = r["data"]
        return {"ok": True, "data": {
            "project_id": p.get("id"),
            "name":       p.get("name"),
            "url":        f"https://{p['name']}.vercel.app",
            "framework":  p.get("framework"),
        }}
