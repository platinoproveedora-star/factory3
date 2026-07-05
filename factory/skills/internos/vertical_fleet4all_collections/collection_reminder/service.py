from __future__ import annotations

from datetime import date
from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "fleet4all"

_STAGE_INSTRUCTIONS = {
    "es": {
        "reminder": "Redacta un recordatorio de cobro amable (el pago vence en 3 dias).",
        "due": "Redacta un aviso de cobro profesional (el pago vence hoy).",
        "overdue_firm": "Redacta un mensaje de cobro firme pero respetuoso (el pago lleva mas de 7 dias vencido). Nunca uses amenazas ni lenguaje agresivo.",
    },
    "en": {
        "reminder": "Write a friendly payment reminder (due in 3 days).",
        "due": "Write a professional payment notice (due today).",
        "overdue_firm": "Write a firm but respectful collection message (payment is more than 7 days overdue). Never use threats or aggressive language.",
    },
}


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class CollectionReminderService:
    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id_requerido"}

        lang = str(context.get("language") or "es").strip().lower()
        if lang not in _STAGE_INSTRUCTIONS:
            lang = "es"
        customer = str(context.get("customer") or "").strip()

        db = SupabaseClient({**context, "schema": _SCHEMA})
        filters = {"empresa_id": f"eq.{empresa_id}", "balance": "gt.0"}
        if customer:
            filters["customer"] = f"eq.{customer}"
        res = db.rest_select("receivables", filters=filters, select="*")
        if not res.get("ok"):
            return {"ok": False, "error": "db_persistence_failed", "data": {"detail": res.get("error")}}
        receivables = res.get("data") or []
        if not receivables:
            return {"ok": False, "error": "no_receivables"}

        today = date.today().isoformat()
        due_receivables = []
        for r in receivables:
            stage = self._stage(r.get("due_date"), today)
            if stage:
                due_receivables.append((r, stage))

        if not due_receivables:
            return {"ok": True, "data": {"reminders": [], "warnings": ["sin receivables en ventana de recordatorio hoy"]}}

        dry_run = context.get("dry_run", True)
        send_channel = context.get("send_channel")
        reminders = []
        warnings = []
        for receivable, stage in due_receivables:
            message = self._draft_message(receivable, stage, lang)
            item = {
                "receivable_folio": receivable.get("receivable_folio"),
                "customer": receivable.get("customer"),
                "stage": stage,
                "message": message,
                "sent": False,
            }
            if not dry_run and send_channel:
                send_res = _runner().run(send_channel, {"to": receivable.get("customer"), "message": message})
                item["sent"] = bool(send_res.get("ok"))
                if not send_res.get("ok"):
                    warnings.append(f"send_failed:{receivable.get('receivable_folio')}:{send_res.get('error')}")
            reminders.append(item)

        return {"ok": True, "data": {"reminders": reminders, "warnings": warnings}}

    def _stage(self, due_date: str | None, today: str) -> str | None:
        if not due_date:
            return None
        days_to_due = (date.fromisoformat(due_date) - date.fromisoformat(today)).days
        if days_to_due == 3:
            return "reminder"
        if -6 <= days_to_due <= 0:
            return "due"
        if days_to_due <= -7:
            return "overdue_firm"
        return None

    def _draft_message(self, receivable: dict, stage: str, lang: str) -> str:
        instruction = _STAGE_INSTRUCTIONS[lang][stage]
        prompt = (
            f"{instruction}\n\n"
            f"Cliente: {receivable.get('customer')}\n"
            f"Folio: {receivable.get('receivable_folio')}\n"
            f"Saldo: {receivable.get('balance')} {receivable.get('currency')}\n"
            f"Fecha de vencimiento: {receivable.get('due_date')}\n\n"
            "Usa solo los datos del adeudo. No amenaces. Firma como el equipo de cobranza."
        )
        result = _runner().run(
            "vertical_factory_utils/ai_interpreter",
            {"mode": "chat", "text": prompt},
        )
        if not result.get("ok"):
            return self._fallback_message(receivable, stage, lang)
        return (result.get("data") or {}).get("response") or self._fallback_message(receivable, stage, lang)

    def _fallback_message(self, receivable: dict, stage: str, lang: str) -> str:
        balance = receivable.get("balance")
        currency = receivable.get("currency")
        folio = receivable.get("receivable_folio")
        due_date = receivable.get("due_date")
        if lang == "en":
            return f"Reminder: invoice {folio} for {balance} {currency} is due {due_date}."
        return f"Recordatorio: el folio {folio} por {balance} {currency} vence el {due_date}."
