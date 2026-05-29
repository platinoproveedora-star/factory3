from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import _vercel_client as vc


class VercelDomainSetupService:
    def ejecutar(self, ctx: dict) -> dict:
        project_id = ctx.get("project_id") or ctx.get("name", "")
        domain     = ctx.get("domain", "").strip().lower()

        if not project_id:
            return {"ok": False, "error": "project_id o name requerido"}
        if not domain:
            return {"ok": False, "error": "domain requerido (ej: dash.cliente.mx)"}

        # Agregar dominio al proyecto
        r = vc.post(f"/v10/projects/{project_id}/domains", body={"name": domain})
        if not r["ok"]:
            return r

        d = r["data"]

        # Consultar configuración DNS requerida
        r_dns = vc.get(f"/v6/domains/{domain}/config")
        dns_info = {}
        if r_dns["ok"]:
            dns_info = r_dns["data"]

        return {"ok": True, "data": {
            "domain":     domain,
            "verified":   d.get("verified", False),
            "project_id": project_id,
            "dns": {
                "misconfigured": dns_info.get("misconfigured", True),
                "cname_record":  dns_info.get("cnames", []),
                "a_record":      dns_info.get("aValues", []),
                "instructions":  (
                    "Apunta CNAME a cname.vercel-dns.com "
                    "o A record a 76.76.21.21"
                ),
            },
        }}
