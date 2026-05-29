from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import _vercel_client as vc


class VercelProjectRemoveService:
    def ejecutar(self, ctx: dict) -> dict:
        project_id = ctx.get("project_id") or ctx.get("name", "")
        confirm    = ctx.get("confirm", False)

        if not project_id:
            return {"ok": False, "error": "project_id o name requerido"}
        if not confirm:
            return {"ok": False, "error": "Agrega confirm:true para confirmar eliminación"}

        # Obtener nombre antes de eliminar
        r_proj = vc.get(f"/v9/projects/{project_id}")
        name = r_proj["data"].get("name", project_id) if r_proj["ok"] else project_id

        r = vc.delete(f"/v9/projects/{project_id}")
        if not r["ok"]:
            return r

        return {"ok": True, "data": {"removed": name, "project_id": project_id}}
