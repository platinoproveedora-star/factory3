"""kind=data — lista filtrable de leads por estado, canal, nivel y fecha. Paginado."""
from __future__ import annotations
import json, os, urllib.request

_SCHEMA  = "sales"
_ESTADOS = {"nuevo", "contactado", "calificado", "propuesta", "ganado", "perdido"}
_CANALES = {"telegram", "whatsapp", "instagram", "web"}


class SalesListService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = context.get("empresa_id", "").strip()
        estado     = context.get("estado", "").strip()
        canal      = context.get("canal", "").strip()
        nivel      = context.get("nivel", "").strip()
        limit      = min(int(context.get("limit", 50)), 200)
        offset     = int(context.get("offset", 0))
        order      = context.get("order", "created_at.desc").strip()

        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if estado and estado not in _ESTADOS:
            return {"ok": False, "error": f"estado inválido — válidos: {', '.join(_ESTADOS)}"}
        if canal and canal not in _CANALES:
            return {"ok": False, "error": f"canal inválido — válidos: {', '.join(_CANALES)}"}

        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return {"ok": False, "error": "Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY"}

        qs = f"empresa_id=eq.{empresa_id}&order={order}&limit={limit}&offset={offset}"
        if estado:
            qs += f"&estado=eq.{estado}"
        if canal:
            qs += f"&canal=eq.{canal}"
        if nivel == "caliente":
            qs += "&score=gte.70"
        elif nivel == "tibio":
            qs += "&score=gte.40&score=lt.70"
        elif nivel == "frio":
            qs += "&score=lt.40"

        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/leads?{qs}&select=id,folio,nombre,telefono,email,canal,estado,fuente,score,created_at,updated_at",
                headers={
                    "apikey":        key,
                    "Authorization": f"Bearer {key}",
                    "Accept-Profile": _SCHEMA,
                    "Prefer":        "count=exact",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                leads = json.loads(r.read().decode())
                total = int(r.headers.get("Content-Range", "*/0").split("/")[-1] or 0)
        except Exception as e:
            return {"ok": False, "error": str(e)}

        for lead in leads:
            s = lead.get("score") or 0
            lead["nivel"] = "caliente" if s >= 70 else "tibio" if s >= 40 else "frio"

        return {"ok": True, "data": {
            "leads":   leads,
            "total":   total,
            "limit":   limit,
            "offset":  offset,
            "filtros": {"estado": estado or None, "canal": canal or None, "nivel": nivel or None},
        }}
