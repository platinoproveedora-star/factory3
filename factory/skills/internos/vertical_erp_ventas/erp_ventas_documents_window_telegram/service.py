from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from factory.engine import SkillLoader, SkillRunner, SupabaseClient


DOCUMENT_LABELS = {
    "pedido": ("pedidos", "Pedidos", "emitidos"),
    "remision": ("remisiones", "Remisiones", "emitidas"),
}


def _text(value: object) -> str:
    return str(value or "").strip()


def _parse_dt(value: str) -> datetime:
    text = str(value or "").replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _money(value: object) -> str:
    try:
        return f"${float(value or 0):,.2f}"
    except Exception:
        return "$0.00"


class ErpVentasDocumentsWindowTelegramService:
    def ejecutar(self, context: dict) -> dict:
        ctx = self._resolve_context(context)
        if not ctx.get("ok"):
            return ctx
        ctx = ctx["data"]
        document_type = _text(context.get("document_type") or context.get("tipo_documento")).lower()
        if document_type not in DOCUMENT_LABELS:
            return {"ok": False, "error": "document_type debe ser pedido o remision"}

        window_hours = max(float(context.get("window_hours") or 2), 0.25)
        now = _parse_dt(_text(context.get("now")) or datetime.now(timezone.utc).isoformat())
        start = now - timedelta(hours=window_hours)
        timezone_name = _text(context.get("timezone") or "America/Mexico_City")
        local_tz = ZoneInfo(timezone_name)
        limit = min(max(int(context.get("limit") or 50), 1), 500)

        result = SupabaseClient(ctx).rest_select(
            "sales_documents",
            filters={
                "empresa_id": f"eq.{ctx['company_id']}",
                "project_code": f"eq.{ctx['project_code']}",
                "module_code": f"eq.{ctx['module_code']}",
                "document_type": f"eq.{document_type}",
                "created_at": f"gte.{start.isoformat()}",
            },
            select="id,folio,external_folio,customer_name_snapshot,status,document_date,subtotal,tax_total,total,balance_total,created_at,notes",
            order="created_at.desc",
            limit=limit,
        )
        if not result.get("ok"):
            return result

        rows = [row for row in (result.get("data") or []) if self._created_at(row) <= now]
        total = sum(float(row.get("total") or 0) for row in rows)
        balance = sum(float(row.get("balance_total") or 0) for row in rows)
        text = self._message(document_type, rows, total, balance, start, now, local_tz)
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"text": text, "count": len(rows), "total": total, "balance": balance}}

        telegram_context = {
            "token": context.get("telegram_token"),
            "token_env": context.get("telegram_token_env") or context.get("token_env"),
            "chat_id": context.get("telegram_chat_id") or context.get("chat_id"),
            "chat_id_env": context.get("telegram_chat_id_env") or context.get("chat_id_env"),
            "text": text,
            "parse_mode": context.get("parse_mode") or "Markdown",
            "dry_run": False,
        }
        sent = self._runner().run("telegram_send_message", telegram_context, source="internos")
        if not sent.get("ok"):
            return sent
        return {"ok": True, "data": {"sent": sent.get("data"), "count": len(rows), "total": total, "balance": balance}}

    def _resolve_context(self, context: dict) -> dict:
        schema = _text(context.get("schema_ventas") or context.get("sales_schema") or context.get("schema"))
        company_id = _text(context.get("company_id") or context.get("empresa_id"))
        project_code = _text(context.get("project_code"))
        module_code = _text(context.get("module_code"))
        missing = []
        if not schema:
            missing.append("schema_ventas/sales_schema")
        if not company_id:
            missing.append("company_id")
        if not project_code:
            missing.append("project_code")
        if not module_code:
            missing.append("module_code")
        if missing:
            return {"ok": False, "error": "faltan en context: " + ", ".join(missing)}
        return {"ok": True, "data": {**context, "schema": schema, "company_id": company_id, "empresa_id": company_id, "project_code": project_code, "module_code": module_code}}

    def _created_at(self, row: dict) -> datetime:
        try:
            return _parse_dt(_text(row.get("created_at")))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    def _message(self, document_type: str, rows: list[dict], total: float, balance: float, start: datetime, now: datetime, local_tz: ZoneInfo) -> str:
        key, title, emitted_label = DOCUMENT_LABELS[document_type]
        start_local = start.astimezone(local_tz).strftime("%d/%m/%Y %H:%M")
        end_local = now.astimezone(local_tz).strftime("%H:%M")
        lines = [
            f"*{title} {emitted_label}*",
            f"Periodo: {start_local} - {end_local}",
            f"Total {key}: *{len(rows)}*",
            f"Importe: *{_money(total)}*",
            f"Saldo: *{_money(balance)}*",
        ]
        if not rows:
            lines.append("Sin documentos en este periodo.")
            return "\n".join(lines)
        lines.append("")
        for row in rows[:25]:
            folio = _text(row.get("folio") or row.get("external_folio") or "sin folio")
            customer = _text(row.get("customer_name_snapshot") or "Sin cliente")
            status = _text(row.get("status") or "sin estatus")
            created = self._created_at(row).astimezone(local_tz).strftime("%H:%M")
            lines.append(f"- {created} | {folio} | {customer} | {_money(row.get('total'))} | {status}")
        if len(rows) > 25:
            lines.append(f"... {len(rows) - 25} mas")
        return "\n".join(lines)

    def _runner(self) -> SkillRunner:
        base = Path(__file__).resolve().parents[5]
        skills_dir = base / "factory" / "skills"
        ext = skills_dir / "externos"
        ext.mkdir(parents=True, exist_ok=True)
        return SkillRunner(SkillLoader(internal_root=skills_dir / "internos", external_root=ext))
