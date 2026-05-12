from __future__ import annotations
import json, os, urllib.request, urllib.parse, urllib.error
from pathlib import Path

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_FIELDS = "id,created_time,field_data"


def _runner():
    from factory.engine import SkillLoader, SkillRunner
    root = Path(__file__).parent.parent.parent
    ext_root = root.parent / "externos"
    ext_root.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(
        internal_root=root,
        external_root=ext_root,
        extra_roots={"meta": root.parent / "meta", "eval": root.parent / "eval"},
    )
    return SkillRunner(loader)


def _run(name: str, ctx: dict) -> dict:
    return _runner().run(name, ctx, source="internos")


class IgLeadsSyncService:

    def ejecutar(self, context: dict) -> dict:
        form_id = (context.get("form_id") or "").strip()
        access_token = (context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN") or "").strip()
        empresa_id = (context.get("empresa_id") or "").strip()
        dry_run = context.get("dry_run", True)
        limit = int(context.get("limit") or 100)

        if not form_id:
            return {"ok": False, "error": "form_id requerido"}
        if not access_token:
            return {"ok": False, "error": "access_token requerido (o IG_ACCESS_TOKEN en env)"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}

        leads_result = self._fetch_leads(form_id, access_token, limit)
        if not leads_result.get("ok"):
            return leads_result

        leads = leads_result["data"]["leads"]
        if not leads:
            return {"ok": True, "data": {"total": 0, "procesados": 0, "errores": 0, "form_id": form_id}}

        if dry_run:
            return {"ok": True, "data": {
                "dry_run":    True,
                "total":      len(leads),
                "form_id":    form_id,
                "muestra":    leads[:3],
            }}

        procesados, errores, detalles = 0, 0, []
        for lead in leads:
            nombre = lead.get("nombre") or ""
            email = lead.get("email") or ""
            telefono = lead.get("telefono") or ""
            texto = f"Lead de formulario IG. Nombre: {nombre}. Email: {email}. Tel: {telefono}."

            r = _run("vertical_sales/sales_run", {
                "canal":      "instagram_lead_form",
                "user_id":    lead.get("lead_id") or "",
                "chat_id":    form_id,
                "texto":      texto,
                "empresa_id": empresa_id,
                "intent":     "consulta_comercial",
                "nombre":     nombre,
                "telefono":   telefono,
                "email":      email,
                "dry_run":    False,
                "raw_payload": {
                    "origen":       "ig_leads_sync",
                    "lead_id":      lead.get("lead_id"),
                    "nombre":       nombre,
                    "email":        email,
                    "telefono":     telefono,
                    "fields":       lead.get("fields", {}),
                    "created_time": lead.get("created_time"),
                    "form_id":      form_id,
                },
            })
            if r.get("ok"):
                procesados += 1
            else:
                errores += 1
                detalles.append({"lead_id": lead.get("lead_id"), "error": r.get("error")})

        return {"ok": True, "data": {
            "total":      len(leads),
            "procesados": procesados,
            "errores":    errores,
            "form_id":    form_id,
            "detalles_errores": detalles if detalles else None,
        }}

    def _fetch_leads(self, form_id: str, token: str, limit: int) -> dict:
        params = {"fields": _FIELDS, "limit": min(limit, 200), "access_token": token}
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{form_id}/leads?{qs}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            if "error" in data:
                return {"ok": False, "error": data["error"].get("message", str(data["error"]))}
            leads_raw = data.get("data", [])
            leads = []
            for l in leads_raw:
                fields = {}
                for item in l.get("field_data", []):
                    vals = item.get("values", [])
                    fields[item.get("name", "")] = vals[0] if len(vals) == 1 else vals
                leads.append({
                    "lead_id":      l.get("id"),
                    "created_time": l.get("created_time"),
                    "fields":       fields,
                    "nombre":       fields.get("full_name") or fields.get("first_name"),
                    "email":        fields.get("email"),
                    "telefono":     fields.get("phone_number") or fields.get("phone"),
                })
            return {"ok": True, "data": {"leads": leads}}
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode())
                msg = err.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
