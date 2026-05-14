from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_FIELDS = "id,created_time,field_data,ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,form_id"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
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


class MetaLeadsSyncToSalesService:
    """Fetches Meta lead form leads and routes them through vertical_sales/sales_run."""

    def ejecutar(self, context: dict) -> dict:
        token = (context.get("access_token") or os.getenv("META_ACCESS_TOKEN") or os.getenv("IG_ACCESS_TOKEN") or "").strip()
        form_id = str(context.get("form_id") or "").strip()
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        dry_run = context.get("dry_run", True)
        limit = int(context.get("limit") or 100)
        mock_leads = context.get("mock_leads") or []

        if not form_id:
            return {"ok": False, "error": "form_id requerido"}
        if not empresa_id:
            return {"ok": False, "error": "empresa_id o company_id requerido"}
        if dry_run and mock_leads:
            leads = [self._normalize_mock_lead(item) for item in mock_leads]
            return {"ok": True, "data": self._dry_summary(form_id, empresa_id, leads)}
        if not token:
            return {"ok": False, "error": "access_token requerido (META_ACCESS_TOKEN o IG_ACCESS_TOKEN)"}

        fetched = self._fetch_leads(form_id, token, limit)
        if not fetched.get("ok"):
            return fetched
        leads = fetched["data"]["leads"]

        if dry_run:
            return {"ok": True, "data": self._dry_summary(form_id, empresa_id, leads)}

        procesados, errores, detalles = 0, 0, []
        for lead in leads:
            sales_context = self._sales_context(lead, empresa_id, form_id, dry_run=False)
            result = _run("vertical_sales/sales_run", sales_context)
            if result.get("ok"):
                procesados += 1
            else:
                errores += 1
                detalles.append({"lead_id": lead.get("lead_id"), "error": result.get("error")})

        return {
            "ok": True,
            "data": {
                "form_id": form_id,
                "empresa_id": empresa_id,
                "total": len(leads),
                "procesados": procesados,
                "errores": errores,
                "detalles_errores": detalles or None,
            },
        }

    def _fetch_leads(self, form_id: str, token: str, limit: int) -> dict:
        params = {"fields": _FIELDS, "limit": min(limit, 200), "access_token": token}
        url = f"https://graph.facebook.com/{_VERSION}/{form_id}/leads?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode())
            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}
            return {"ok": True, "data": {"leads": [self._normalize_lead(item) for item in data.get("data", [])]}}
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode())
                message = err.get("error", {}).get("message", str(exc))
            except Exception:
                message = str(exc)
            return {"ok": False, "error": message}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _normalize_lead(self, item: dict) -> dict:
        fields = {}
        for field in item.get("field_data", []):
            values = field.get("values", [])
            fields[field.get("name", "")] = values[0] if len(values) == 1 else values
        return {
            "lead_id": item.get("id"),
            "created_time": item.get("created_time"),
            "form_id": item.get("form_id"),
            "campaign_id": item.get("campaign_id"),
            "campaign_name": item.get("campaign_name"),
            "adset_id": item.get("adset_id"),
            "adset_name": item.get("adset_name"),
            "ad_id": item.get("ad_id"),
            "ad_name": item.get("ad_name"),
            "fields": fields,
            "nombre": fields.get("full_name") or fields.get("first_name") or fields.get("nombre_completo"),
            "email": fields.get("email"),
            "telefono": fields.get("phone_number") or fields.get("phone") or fields.get("telefono"),
        }

    def _normalize_mock_lead(self, item: dict) -> dict:
        if "fields" in item:
            return item
        fields = dict(item)
        return {
            "lead_id": item.get("lead_id") or item.get("id") or "mock-lead",
            "created_time": item.get("created_time"),
            "fields": fields,
            "nombre": item.get("nombre") or item.get("full_name"),
            "email": item.get("email"),
            "telefono": item.get("telefono") or item.get("phone"),
        }

    def _dry_summary(self, form_id: str, empresa_id: str, leads: list[dict]) -> dict:
        return {
            "dry_run": True,
            "form_id": form_id,
            "empresa_id": empresa_id,
            "total": len(leads),
            "muestra": leads[:3],
            "accion": "fetch_meta_leads_then_route_to_vertical_sales_sales_run",
            "sales_context_sample": self._sales_context(leads[0], empresa_id, form_id, dry_run=True) if leads else None,
        }

    def _sales_context(self, lead: dict, empresa_id: str, form_id: str, dry_run: bool) -> dict:
        fields = lead.get("fields") or {}
        nombre = lead.get("nombre") or ""
        telefono = lead.get("telefono") or ""
        email = lead.get("email") or ""
        field_text = "; ".join(f"{key}: {value}" for key, value in fields.items() if value)
        texto = f"Lead de formulario Meta. Nombre: {nombre}. Email: {email}. Tel: {telefono}. {field_text}".strip()
        return {
            "canal": "instagram_lead_form",
            "user_id": str(lead.get("lead_id") or ""),
            "chat_id": form_id,
            "texto": texto,
            "empresa_id": empresa_id,
            "intent": "consulta_comercial",
            "nombre": nombre,
            "telefono": telefono,
            "email": email,
            "dry_run": dry_run,
            "raw_payload": {
                "origen": "meta_leads_sync_to_sales",
                "lead": lead,
                "form_id": form_id,
            },
        }
