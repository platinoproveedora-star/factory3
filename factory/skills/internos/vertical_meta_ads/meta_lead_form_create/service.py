from __future__ import annotations
import json, os, urllib.error, urllib.parse, urllib.request

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_FIELD_TYPES = {
    "FULL_NAME", "EMAIL", "PHONE", "CITY", "REGION", "COUNTRY",
    "DATE_TIME", "JOB_TITLE", "COMPANY_NAME", "WORK_EMAIL",
    "WORK_PHONE_NUMBER", "CUSTOM",
}

_PRESETS = {
    "reclutamiento_chofer_torton": {
        "form_name": "Reclutamiento - Chofer Torton",
        "questions": [
            "FULL_NAME",
            "PHONE",
            {"type": "CUSTOM", "label": "Ciudad o zona donde vives"},
            {"type": "CUSTOM", "label": "Anios de experiencia manejando torton", "options": ["Menos de 1", "1 a 2", "3 a 5", "Mas de 5"]},
            {"type": "CUSTOM", "label": "Tienes licencia vigente?", "options": ["Si", "No"]},
            {"type": "CUSTOM", "label": "Que tipo de licencia tienes?"},
            {"type": "CUSTOM", "label": "Puedes hacer rutas foraneas?", "options": ["Si", "No", "Depende la ruta"]},
            {"type": "CUSTOM", "label": "Puedes iniciar esta semana?", "options": ["Si", "No"]},
        ],
    },
    "inmobiliaria_venta_propiedades": {
        "form_name": "Lead Inmobiliaria - Venta de Propiedades",
        "questions": [
            "FULL_NAME",
            "PHONE",
            "EMAIL",
            {"type": "CUSTOM", "label": "Que tipo de propiedad buscas?", "options": ["Casa", "Departamento", "Terreno", "Local comercial", "Otro"]},
            {"type": "CUSTOM", "label": "Zona o ciudad de interes"},
            {"type": "CUSTOM", "label": "Presupuesto aproximado", "options": ["Menos de $1M", "$1M a $2M", "$2M a $4M", "Mas de $4M"]},
            {"type": "CUSTOM", "label": "Forma de compra", "options": ["Contado", "Credito bancario", "Infonavit/Fovissste", "Aun no lo se"]},
            {"type": "CUSTOM", "label": "Cuando quieres comprar?", "options": ["Este mes", "1 a 3 meses", "3 a 6 meses", "Solo estoy explorando"]},
            {"type": "CUSTOM", "label": "Ya tienes credito preaprobado?", "options": ["Si", "No", "En tramite"]},
        ],
    },
}
_DEFAULT_PRESET = "reclutamiento_chofer_torton"


class MetaLeadFormCreateService:

    def ejecutar(self, context: dict) -> dict:
        token = (context.get("access_token") or os.getenv("META_ACCESS_TOKEN") or os.getenv("IG_ACCESS_TOKEN") or "").strip()
        page_id = (context.get("page_id") or os.getenv("META_PAGE_ID") or os.getenv("IG_PAGE_ID") or "").strip()
        preset_name = (context.get("preset") or _DEFAULT_PRESET).strip()
        preset = _PRESETS.get(preset_name)
        if not preset:
            return {"ok": False, "error": f"preset invalido. Opciones: {sorted(_PRESETS)}"}

        form_name = (context.get("form_name") or context.get("nombre") or preset["form_name"]).strip()
        privacy_url = (context.get("privacy_url") or os.getenv("META_PRIVACY_URL") or "").strip()
        preguntas = context.get("preguntas") or context.get("questions") or preset["questions"]

        if not token:
            return {"ok": False, "error": "access_token requerido (META_ACCESS_TOKEN o IG_ACCESS_TOKEN)"}
        if not page_id:
            return {"ok": False, "error": "page_id requerido (META_PAGE_ID o IG_PAGE_ID)"}
        if not privacy_url:
            return {"ok": False, "error": "privacy_url requerido (META_PRIVACY_URL)"}

        questions = self._build_questions(preguntas)
        if isinstance(questions, dict) and not questions.get("ok", True):
            return questions

        payload = {
            "name": form_name,
            "questions": json.dumps(questions),
            "privacy_policy": json.dumps({"url": privacy_url}),
            "locale": context.get("locale", "es_LA"),
        }
        if context.get("follow_up_action_url"):
            payload["follow_up_action_url"] = context["follow_up_action_url"]
        if context.get("thank_you_page"):
            payload["thank_you_page"] = json.dumps(context["thank_you_page"])

        if context.get("dry_run", True):
            return {"ok": True, "data": {
                "dry_run": True,
                "form_name": form_name,
                "preset": preset_name,
                "page_id": page_id,
                "privacy_url": privacy_url,
                "questions_count": len(questions),
                "questions": questions,
            }}

        try:
            data = self._post(f"{page_id}/leadgen_forms", payload, token)
            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}
            return {"ok": True, "data": {"form_id": data.get("id"), "form_name": form_name, "page_id": page_id}}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": self._http_error(exc)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _build_questions(self, preguntas: list) -> list | dict:
        result = []
        for i, pregunta in enumerate(preguntas):
            if isinstance(pregunta, str):
                q_type = pregunta.upper()
                if q_type not in _FIELD_TYPES:
                    return {"ok": False, "error": f"Tipo de pregunta invalido: {pregunta}"}
                result.append({"type": q_type})
                continue

            if not isinstance(pregunta, dict):
                return {"ok": False, "error": f"Pregunta #{i + 1} debe ser texto o dict"}

            q_type = (pregunta.get("type") or pregunta.get("tipo") or "CUSTOM").upper()
            if q_type not in _FIELD_TYPES:
                return {"ok": False, "error": f"Tipo de pregunta invalido: {q_type}"}
            item = {"type": q_type}
            if q_type == "CUSTOM":
                item["label"] = pregunta.get("label") or pregunta.get("pregunta") or f"Pregunta {i + 1}"
                options = pregunta.get("options") or pregunta.get("opciones")
                if options:
                    item["options"] = [{"value": str(option)} for option in options]
            result.append(item)
        return result

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    def _http_error(self, exc: urllib.error.HTTPError) -> str:
        try:
            err = json.loads(exc.read().decode())
            return err.get("error", {}).get("message", str(exc))
        except Exception:
            return str(exc)
