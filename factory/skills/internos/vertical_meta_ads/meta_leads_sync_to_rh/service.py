from __future__ import annotations
import json, os, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_FIELDS = "id,created_time,field_data,ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,form_id"


def _add_repo_root() -> None:
    root = Path(__file__).resolve().parents[5]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


class MetaLeadsSyncToRhService:

    def ejecutar(self, context: dict) -> dict:
        token = (context.get("access_token") or os.getenv("META_ACCESS_TOKEN") or os.getenv("IG_ACCESS_TOKEN") or "").strip()
        form_id = (context.get("form_id") or "").strip()
        vacante_id = (context.get("vacante_id") or "").strip()
        empresa_id = (context.get("empresa_id") or os.getenv("RH_EMPRESA_ID") or "platino_logistica").strip()
        limit = int(context.get("limit") or 100)

        if not token:
            return {"ok": False, "error": "access_token requerido (META_ACCESS_TOKEN)"}
        if not form_id:
            return {"ok": False, "error": "form_id requerido"}

        if context.get("dry_run", True):
            mock_leads = context.get("mock_leads") or []
            return {"ok": True, "data": {
                "dry_run": True,
                "form_id": form_id,
                "vacante_id": vacante_id or None,
                "empresa_id": empresa_id,
                "total_mock": len(mock_leads),
                "muestra": mock_leads[:3],
                "accion": "fetch_leads_graph_api_then_insert_candidatos",
            }}

        fetched = self._fetch_leads(form_id, token, limit)
        if not fetched.get("ok"):
            return fetched
        leads = fetched["data"]["leads"]

        _add_repo_root()
        from factory.engine.supabase_client import SupabaseClient

        db = SupabaseClient(context)
        check = db.check_config(require_rest=True)
        if not check.get("ok"):
            return check

        procesados, duplicados, errores = 0, 0, []
        for lead in leads:
            existing = self._find_existing(db, lead)
            if existing:
                duplicados += 1
                self._insert_respuestas(db, existing.get("id"), vacante_id, lead)
                continue

            row = {
                "empresa_id": empresa_id,
                "vacante_id": vacante_id or None,
                "nombre": lead.get("nombre") or None,
                "telefono": lead.get("telefono") or None,
                "email": lead.get("email") or None,
                "canal": "meta_lead_ads",
                "canal_user_id": lead.get("lead_id"),
                "estado": "nuevo",
            }
            inserted = db.rest_insert("candidatos", row)
            if not inserted.get("ok"):
                errores.append({"lead_id": lead.get("lead_id"), "error": inserted.get("error")})
                continue

            candidato = (inserted.get("data") or [{}])[0] if isinstance(inserted.get("data"), list) else {}
            self._insert_respuestas(db, candidato.get("id"), vacante_id, lead)
            procesados += 1

        return {"ok": True, "data": {
            "form_id": form_id,
            "total": len(leads),
            "procesados": procesados,
            "duplicados": duplicados,
            "errores": len(errores),
            "detalles_errores": errores or None,
        }}

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
                msg = err.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
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

    def _find_existing(self, db, lead: dict) -> dict | None:
        lead_id = lead.get("lead_id")
        if lead_id:
            result = db.rest_select("candidatos", filters={"canal_user_id": lead_id}, select="id", limit=1)
            rows = result.get("data") or []
            if result.get("ok") and rows:
                return rows[0]
        phone = lead.get("telefono")
        if phone:
            result = db.rest_select("candidatos", filters={"telefono": phone}, select="id", limit=1)
            rows = result.get("data") or []
            if result.get("ok") and rows:
                return rows[0]
        return None

    def _insert_respuestas(self, db, candidato_id: str | None, vacante_id: str, lead: dict) -> None:
        if not candidato_id:
            return
        rows = []
        for order, (question, answer) in enumerate((lead.get("fields") or {}).items(), start=1):
            rows.append({
                "candidato_id": candidato_id,
                "vacante_id": vacante_id or None,
                "pregunta": question,
                "respuesta": json.dumps(answer, ensure_ascii=True) if isinstance(answer, (list, dict)) else str(answer),
                "orden": order,
            })
        if rows:
            db.rest_insert("respuestas", rows)
