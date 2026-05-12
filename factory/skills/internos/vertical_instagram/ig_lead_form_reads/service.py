from __future__ import annotations
import json, os, urllib.request, urllib.parse, urllib.error

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_FIELDS = "id,created_time,field_data"


class IgLeadFormReadsService:

    def ejecutar(self, context: dict) -> dict:
        form_id = (context.get("form_id") or "").strip()
        access_token = (context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN") or "").strip()
        limit = int(context.get("limit") or 100)
        after = context.get("after")

        if not form_id:
            return {"ok": False, "error": "form_id requerido"}
        if not access_token:
            return {"ok": False, "error": "access_token requerido (o IG_ACCESS_TOKEN en env)"}

        params = {
            "fields": _FIELDS,
            "limit":  min(limit, 200),
        }
        if after:
            params["after"] = after

        try:
            data = self._get(f"{form_id}/leads", params, access_token)
            if "error" in data:
                return {"ok": False, "error": data["error"].get("message", str(data["error"]))}

            leads_raw = data.get("data", [])
            leads = [self._normalize(l) for l in leads_raw]

            paging = data.get("paging", {})
            cursors = paging.get("cursors", {})

            return {"ok": True, "data": {
                "leads":      leads,
                "total":      len(leads),
                "form_id":    form_id,
                "next_cursor": cursors.get("after"),
                "has_more":   bool(paging.get("next")),
            }}
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode())
                msg = err.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _normalize(self, lead: dict) -> dict:
        fields = {}
        for item in lead.get("field_data", []):
            key = item.get("name", "")
            values = item.get("values", [])
            fields[key] = values[0] if len(values) == 1 else values
        return {
            "lead_id":      lead.get("id"),
            "created_time": lead.get("created_time"),
            "fields":       fields,
            "nombre":       fields.get("full_name") or fields.get("first_name"),
            "email":        fields.get("email"),
            "telefono":     fields.get("phone_number") or fields.get("phone"),
        }

    def _get(self, path: str, params: dict, token: str) -> dict:
        params["access_token"] = token
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{path}?{qs}"
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
