from __future__ import annotations

from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"

_CONFIRM_WORDS = {"confirmar", "confirm", "si", "yes", "sí"}
_CANCEL_WORDS = {"cancelar", "cancel", "no"}

MESSAGES = {
    "es": {
        "help": (
            "*Fleet4All*\n\n"
            "*Registrar viaje:*\n"
            "Escribe: viaje\n"
            "Luego: `cliente,origen,destino,precio`\n"
            "Ej: `Cliente X,CDMX,Monterrey,15000`\n\n"
            "*Registrar gasto:*\n"
            "Escribe: gasto\n"
            "Luego: `monto,concepto,dd/mm/aa,viaje(opcional)`\n"
            "Ej: `500,gasolina,05/07/26,T-0025`\n"
            "O envía una foto del comprobante.\n\n"
            "Escribe *ayuda* para ver este mensaje de nuevo."
        ),
        "prompt_trip": "Envía el viaje:\n`cliente,origen,destino,precio`\nEj: `Cliente X,CDMX,Monterrey,15000`",
        "prompt_expense": (
            "Envía el gasto:\n`monto,concepto,dd/mm/aa,viaje(opcional)`\n"
            "Ej: `500,gasolina,05/07/26,T-0025`\n\nO envía una foto del comprobante."
        ),
        "invalid_trip": "Formato incorrecto. Usa: `cliente,origen,destino,precio`",
        "invalid_expense": "Formato incorrecto. Usa: `monto,concepto,dd/mm/aa,viaje(opcional)`",
        "trip_not_found": "No encontré ese viaje. Verifica el folio.",
        "trip_not_active": "Ese viaje ya está cerrado, no acepta más gastos.",
        "no_empresa": "Tu número no está registrado en ninguna empresa Fleet4All. Contacta a tu administrador.",
        "unknown": "Escribe *gasto* para registrar un gasto, *viaje* para registrar un viaje, o *ayuda*.",
        "trip_saved": "✅ Viaje *{folio}* registrado.\n{origin} → {destination}\nVenta: {sale_price} {currency}",
        "expense_saved": "✅ Gasto *{folio}* registrado.\nConcepto: {concept}\nMonto: {amount} {expense_type}",
        "error_saving": "No pude guardar: {error}",
        "expense_draft_confirm": (
            "📷 Leí en el comprobante:\nMonto: {amount}\nConcepto: {concept}\nFecha: {expense_date}\n\n"
            "Escribe *confirmar* para guardar o *cancelar* para descartar."
        ),
        "draft_cancelled": "Gasto descartado.",
        "draft_reprompt": "Escribe *confirmar* para guardar o *cancelar* para descartar.",
        "media_error": "No pude leer el archivo: {error}",
    },
    "en": {
        "help": (
            "*Fleet4All*\n\n"
            "*Log a trip:*\n"
            "Type: trip\n"
            "Then: `customer,origin,destination,price`\n"
            "Eg: `Customer X,CDMX,Monterrey,15000`\n\n"
            "*Log an expense:*\n"
            "Type: expense\n"
            "Then: `amount,concept,dd/mm/yy,trip(optional)`\n"
            "Eg: `500,fuel,05/07/26,T-0025`\n"
            "Or send a photo of the receipt.\n\n"
            "Type *help* to see this message again."
        ),
        "prompt_trip": "Send the trip:\n`customer,origin,destination,price`\nEg: `Customer X,CDMX,Monterrey,15000`",
        "prompt_expense": (
            "Send the expense:\n`amount,concept,dd/mm/yy,trip(optional)`\n"
            "Eg: `500,fuel,05/07/26,T-0025`\n\nOr send a photo of the receipt."
        ),
        "invalid_trip": "Wrong format. Use: `customer,origin,destination,price`",
        "invalid_expense": "Wrong format. Use: `amount,concept,dd/mm/yy,trip(optional)`",
        "trip_not_found": "I couldn't find that trip. Check the folio.",
        "trip_not_active": "That trip is already closed, it can't take more expenses.",
        "no_empresa": "Your phone number isn't registered with any Fleet4All company. Contact your admin.",
        "unknown": "Type *expense* to log an expense, *trip* to log a trip, or *help*.",
        "trip_saved": "✅ Trip *{folio}* saved.\n{origin} → {destination}\nSale: {sale_price} {currency}",
        "expense_saved": "✅ Expense *{folio}* saved.\nConcept: {concept}\nAmount: {amount} {expense_type}",
        "error_saving": "Couldn't save: {error}",
        "expense_draft_confirm": (
            "📷 I read from the receipt:\nAmount: {amount}\nConcept: {concept}\nDate: {expense_date}\n\n"
            "Type *confirm* to save or *cancel* to discard."
        ),
        "draft_cancelled": "Expense discarded.",
        "draft_reprompt": "Type *confirm* to save or *cancel* to discard.",
        "media_error": "Couldn't read the file: {error}",
    },
}


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class FleetMessageHandlerService:
    def ejecutar(self, context: dict) -> dict:
        from_phone = str(context.get("from_phone") or "").strip()
        if not from_phone:
            return {"ok": False, "error": "from_phone_requerido"}

        lang = str(context.get("language") or "es").strip().lower()
        if lang not in MESSAGES:
            lang = "es"
        msg_type = context.get("type", "text")
        body = str(context.get("body") or "").strip()
        media_id = context.get("media_id") or ""
        dry_run = context.get("dry_run", True)

        empresa_id = self._resolve_empresa_id(context, from_phone)
        if not empresa_id:
            return {"ok": True, "data": {"reply": self._t(lang, "no_empresa")}}

        chat_id = f"fleet4all_{empresa_id}_{from_phone}"
        state = self._load_state(chat_id)
        hint = state.get("hint", "")
        text_lower = body.lower().lstrip("/")
        new_state = dict(state)
        reply = ""

        if msg_type == "text" and text_lower in ("ayuda", "help"):
            reply = self._t(lang, "help")
            new_state = {}
        elif msg_type == "text" and text_lower in ("gasto", "expense"):
            new_state = {"hint": "expense"}
            reply = self._t(lang, "prompt_expense")
        elif msg_type == "text" and text_lower in ("viaje", "trip"):
            new_state = {"hint": "trip"}
            reply = self._t(lang, "prompt_trip")
        elif hint == "expense_confirm":
            reply, new_state = self._handle_confirm(text_lower, state, empresa_id, dry_run, lang)
        elif hint == "expense":
            if msg_type in ("image", "document") and media_id:
                reply, new_state = self._handle_expense_media(media_id, empresa_id, state, lang)
            elif msg_type == "text" and body:
                reply, new_state = self._handle_expense_text(body, empresa_id, dry_run, lang)
            else:
                reply, new_state = self._t(lang, "prompt_expense"), state
        elif hint == "trip":
            if msg_type == "text" and body:
                reply, new_state = self._handle_trip_text(body, empresa_id, dry_run, lang)
            else:
                reply, new_state = self._t(lang, "prompt_trip"), state
        else:
            reply, new_state = self._t(lang, "unknown"), state

        if not dry_run:
            self._save_state(chat_id, new_state)

        return {"ok": True, "data": {"reply": reply}}

    # ── HANDLERS ──────────────────────────────────────────────────────────────

    def _handle_trip_text(self, body: str, empresa_id: str, dry_run: bool, lang: str) -> tuple[str, dict]:
        parts = [p.strip() for p in body.split(",")]
        if len(parts) != 4:
            return self._t(lang, "invalid_trip"), {"hint": "trip"}
        customer, origin, destination, sale_price = parts
        res = _runner().run(
            "vertical_fleet4all_trips/trip_create",
            {
                "empresa_id": empresa_id,
                "customer": customer,
                "origin": origin,
                "destination": destination,
                "sale_price": sale_price,
                "dry_run": dry_run,
            },
        )
        if not res.get("ok"):
            if res.get("error") == "invalid_amount":
                return self._t(lang, "invalid_trip"), {"hint": "trip"}
            return self._t(lang, "error_saving", error=res.get("error")), {}
        trip = (res.get("data") or {}).get("trip") or {}
        return self._t(
            lang,
            "trip_saved",
            folio=trip.get("trip_folio") or "?",
            origin=trip.get("origin"),
            destination=trip.get("destination"),
            sale_price=trip.get("sale_price"),
            currency=trip.get("currency"),
        ), {}

    def _handle_expense_text(self, body: str, empresa_id: str, dry_run: bool, lang: str) -> tuple[str, dict]:
        res = _runner().run(
            "vertical_fleet4all_trips/expense_capture",
            {"empresa_id": empresa_id, "text": body, "dry_run": dry_run},
        )
        return self._reply_from_expense_result(res, lang)

    def _handle_expense_media(self, media_id: str, empresa_id: str, state: dict, lang: str) -> tuple[str, dict]:
        dl = _runner().run("vertical_wabiz/wabiz_media_downloader", {"media_id": media_id, "empresa_id": empresa_id})
        if not dl.get("ok"):
            return self._t(lang, "media_error", error=dl.get("error")), state
        content_b64 = (dl.get("data") or {}).get("content_b64")
        mime_type = (dl.get("data") or {}).get("mime_type") or "image/jpeg"
        res = _runner().run(
            "vertical_fleet4all_trips/expense_capture",
            {"empresa_id": empresa_id, "image_base64": content_b64, "media_type": mime_type},
        )
        if not res.get("ok"):
            return self._t(lang, "error_saving", error=res.get("error")), state
        draft = (res.get("data") or {}).get("expense_draft") or {}
        new_state = {"hint": "expense_confirm", "draft": draft}
        return self._t(
            lang,
            "expense_draft_confirm",
            amount=draft.get("amount"),
            concept=draft.get("concept"),
            expense_date=draft.get("expense_date"),
        ), new_state

    def _handle_confirm(self, text_lower: str, state: dict, empresa_id: str, dry_run: bool, lang: str) -> tuple[str, dict]:
        if text_lower in _CANCEL_WORDS:
            return self._t(lang, "draft_cancelled"), {}
        if text_lower not in _CONFIRM_WORDS:
            return self._t(lang, "draft_reprompt"), state
        draft = state.get("draft") or {}
        res = _runner().run(
            "vertical_fleet4all_trips/expense_capture",
            {
                "empresa_id": empresa_id,
                "confirmed": True,
                "amount": draft.get("amount"),
                "concept": draft.get("concept"),
                "expense_date": draft.get("expense_date"),
                "dry_run": dry_run,
            },
        )
        return self._reply_from_expense_result(res, lang)

    def _reply_from_expense_result(self, res: dict, lang: str) -> tuple[str, dict]:
        if not res.get("ok"):
            error = res.get("error")
            if error in ("invalid_amount", "missing_required_fields"):
                return self._t(lang, "invalid_expense"), {"hint": "expense"}
            if error in ("trip_not_found", "trip_not_active"):
                return self._t(lang, error), {"hint": "expense"}
            return self._t(lang, "error_saving", error=error), {}
        expense = (res.get("data") or {}).get("expense") or {}
        return self._t(
            lang,
            "expense_saved",
            folio=expense.get("expense_folio") or "?",
            concept=expense.get("concept"),
            amount=expense.get("amount"),
            expense_type=expense.get("expense_type"),
        ), {}

    # ── EMPRESA RESOLUTION ───────────────────────────────────────────────────

    def _resolve_empresa_id(self, context: dict, from_phone: str) -> str | None:
        explicit = str(context.get("empresa_id") or "").strip()
        if explicit:
            return explicit
        registry = context.get("phone_registry")
        if isinstance(registry, dict) and from_phone in registry:
            return str(registry[from_phone]).strip() or None
        db = SupabaseClient({**context, "schema": _SCHEMA})
        res = db.rest_select("drivers", filters={"phone": f"eq.{from_phone}"}, select="empresa_id", limit=1)
        rows = (res.get("data") or []) if res.get("ok") else []
        return rows[0].get("empresa_id") if rows else None

    # ── STATE ────────────────────────────────────────────────────────────────

    def _load_state(self, chat_id: str) -> dict:
        db = SupabaseClient({"schema": "public"})
        res = db.rest_select("bot_states", filters={"chat_id": f"eq.{chat_id}"}, select="state", limit=1)
        rows = (res.get("data") or []) if res.get("ok") else []
        return (rows[0].get("state") or {}) if rows else {}

    def _save_state(self, chat_id: str, state: dict) -> None:
        db = SupabaseClient({"schema": "public"})
        existing = db.rest_select("bot_states", filters={"chat_id": f"eq.{chat_id}"}, select="chat_id", limit=1)
        rows = (existing.get("data") or []) if existing.get("ok") else []
        if rows:
            db.rest_update("bot_states", values={"state": state}, filters={"chat_id": f"eq.{chat_id}"})
        else:
            db.rest_insert("bot_states", {"chat_id": chat_id, "state": state})

    # ── I18N ─────────────────────────────────────────────────────────────────

    def _t(self, lang: str, key: str, **kwargs) -> str:
        template = MESSAGES.get(lang, MESSAGES["es"]).get(key) or MESSAGES["es"].get(key, key)
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
