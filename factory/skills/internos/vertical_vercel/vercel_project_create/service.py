from __future__ import annotations
import importlib.util as _ilu
from pathlib import Path

_VC_PATH = Path(__file__).parent.parent / "_vercel_client.py"
_vc_spec = _ilu.spec_from_file_location("_vercel_client", _VC_PATH)
vc       = _ilu.module_from_spec(_vc_spec)
_vc_spec.loader.exec_module(vc)


class VercelProjectCreateService:
    def ejecutar(self, ctx: dict) -> dict:
        name      = ctx.get("name", "").strip()
        repo      = ctx.get("repo", "").strip()       # "org/repo-name"
        framework = ctx.get("framework", "nextjs")
        root_dir  = ctx.get("root_dir", "")
        dry_run   = ctx.get("dry_run", True)

        if not name:
            return {"ok": False, "error": "name requerido"}

        if dry_run:
            return {"ok": True, "data": {
                "dry_run": True,
                "preview": {"name": name, "repo": repo, "framework": framework},
            }}

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
