from __future__ import annotations
import json, os, urllib.request, urllib.parse, urllib.error

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"

_FIELD_TYPES = {
    "FULL_NAME", "EMAIL", "PHONE", "CITY", "REGION", "COUNTRY",
    "DATE_TIME", "JOB_TITLE", "COMPANY_NAME", "WORK_EMAIL",
    "WORK_PHONE_NUMBER", "MARITAL_STATUS", "RELATIONSHIP_STATUS",
    "MILITARY_STATUS", "CUSTOM",
}


class IgLeadFormCreateService:

    def ejecutar(self, context: dict) -> dict:
        page_id = (context.get("page_id") or os.getenv("IG_PAGE_ID") or os.getenv("META_PAGE_ID") or "").strip()
        access_token = (context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN") or "").strip()
        form_name = (context.get("form_name") or context.get("nombre") or "").strip()
        preguntas = context.get("preguntas") or []

        if not page_id:
            return {"ok": False, "error": "page_id requerido (o IG_PAGE_ID en env)"}
        if not access_token:
            return {"ok": False, "error": "access_token requerido (o IG_ACCESS_TOKEN en env)"}
        if not form_name:
            return {"ok": False, "error": "form_name requerido"}
        if not preguntas or not isinstance(preguntas, list):
            return {"ok": False, "error": "preguntas debe ser lista no vacía"}

        questions = self._build_questions(preguntas)
        if isinstance(questions, dict) and not questions.get("ok", True):
            return questions

        if context.get("dry_run", True):
            return {"ok": True, "data": {
                "dry_run": True,
                "form_name": form_name,
                "page_id": page_id,
                "questions_count": len(questions),
            }}

        privacy_url = context.get("privacy_url") or os.getenv("META_PRIVACY_URL", "https://example.com/privacidad")
        payload = {
            "name":          form_name,
            "questions":     json.dumps(questions),
            "privacy_policy": json.dumps({"url": privacy_url}),
            "locale":        context.get("locale", "es_LA"),
        }
        if context.get("follow_up_action_url"):
            payload["follow_up_action_url"] = context["follow_up_action_url"]

        try:
            data = self._post(f"{page_id}/leadgen_forms", payload, access_token)
            if "error" in data:
                return {"ok": False, "error": data["error"].get("message", str(data["error"]))}
            return {"ok": True, "data": {
                "form_id":   data.get("id"),
                "form_name": form_name,
                "page_id":   page_id,
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

    def _build_questions(self, preguntas: list) -> list:
        result = []
        for i, p in enumerate(preguntas):
            if isinstance(p, str):
                tipo = p.upper()
                if tipo not in _FIELD_TYPES:
                    return {"ok": False, "error": f"Tipo de pregunta inválido: '{p}'. Válidos: {sorted(_FIELD_TYPES)}"}
                result.append({"type": tipo})
            elif isinstance(p, dict):
                tipo = (p.get("type") or p.get("tipo") or "CUSTOM").upper()
                q = {"type": tipo}
                if tipo == "CUSTOM":
                    label = p.get("label") or p.get("pregunta") or f"Pregunta {i+1}"
                    q["label"] = label
                    if p.get("opciones") or p.get("options"):
                        opciones = p.get("opciones") or p.get("options")
                        q["options"] = [{"value": str(o)} for o in opciones]
                result.append(q)
        return result

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
