from __future__ import annotations
import importlib.util as _ilu
from pathlib import Path

_VC_PATH = Path(__file__).parent.parent / "_vercel_client.py"
_vc_spec = _ilu.spec_from_file_location("_vercel_client", _VC_PATH)
vc       = _ilu.module_from_spec(_vc_spec)
_vc_spec.loader.exec_module(vc)


class VercelProjectRemoveService:
    def ejecutar(self, ctx: dict) -> dict:
        project_id = ctx.get("project_id") or ctx.get("name", "")
        confirm    = ctx.get("confirm", False)

        dry_run = ctx.get("dry_run", True)

        if not project_id:
            return {"ok": False, "error": "project_id o name requerido"}
        if not confirm:
            return {"ok": False, "error": "Agrega confirm:true para confirmar eliminación"}

        if dry_run:
            return {"ok": True, "data": {
                "dry_run": True,
                "preview": {"would_remove": project_id},
            }}

        # Obtener nombre antes de eliminar
        r_proj = vc.get(f"/v9/projects/{project_id}")
        name = r_proj["data"].get("name", project_id) if r_proj["ok"] else project_id

        r = vc.delete(f"/v9/projects/{project_id}")
        if not r["ok"]:
            return r

        return {"ok": True, "data": {"removed": name, "project_id": project_id}}
