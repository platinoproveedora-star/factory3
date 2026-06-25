from __future__ import annotations
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, money, resolve_billing_context  # noqa: E402

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_UUID_RE = re.compile(r"^[0-9a-f\-]{36}$", re.I)


class ErpBillingConciliacionDataService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        banks_schema = blank(context.get("banks_schema") or ctx.get("banks_schema"))
        if not banks_schema:
            return {"ok": False, "error": "banks_schema requerido para conciliacion (ej. uc101_banks)"}

        today = date.today()
        date_to = blank(context.get("date_to")) or today.isoformat()
        date_from = blank(context.get("date_from")) or (today - timedelta(days=30)).isoformat()
        account_id = blank(context.get("account_id"))

        # ── Pagos de cobranza (billing schema — REST funciona) ──────────────────
        billing_db = SupabaseClient(ctx)
        pay_r = billing_db.rest_select(
            "billing_payments",
            filters={},
            select="id,folio,customer_name,amount,payment_date,payment_method,confirmation_status,status",
            limit=1000,
            order="payment_date.desc",
        )
        all_payments = pay_r.get("data") or [] if pay_r.get("ok") else []
        payments = [
            p for p in all_payments
            if date_from <= (p.get("payment_date") or "") <= date_to
            and p.get("status") != "cancelado"
        ]

        # ── Movimientos bancarios (banks schema — Management API requerido) ──────
        # uc101_banks no está expuesto en Data API; usamos management_query
        account_clause = ""
        if account_id and _UUID_RE.match(account_id):
            account_clause = f" AND account_id = '{account_id}'"

        sql = f"""
            SELECT id, folio, account_id, account_folio, amount::float,
                   movement_date, source_folio, source_id, source_type, notes, metadata
            FROM {banks_schema}.banks_movements
            WHERE movement_type = 'entrada'
              AND movement_date >= '{date_from}'
              AND movement_date <= '{date_to}'
              {account_clause}
            ORDER BY movement_date DESC
            LIMIT 500
        """
        mov_r = SupabaseClient(ctx).management_query(sql)
        movements = mov_r.get("data") or [] if mov_r.get("ok") else []

        # ── Cruces manuales ya registrados ──────────────────────────────────────
        # Guardamos dict {movement_id: payment_id} para reconstruir correctamente
        manual_map: dict = {}  # movement_id → payment_id
        try:
            mc_r = billing_db.rest_select(
                "billing_conciliacion_matches",
                filters={"status": "eq.activo"},
                select="movement_id,payment_id,match_type",
                limit=500,
            )
            if mc_r.get("ok"):
                for mm in (mc_r.get("data") or []):
                    mid = mm.get("movement_id")
                    pid = mm.get("payment_id")
                    if mid and pid:
                        manual_map[mid] = pid
        except Exception:
            pass

        payments_by_folio = {p["folio"]: p for p in payments if p.get("folio")}
        payments_by_id = {p["id"]: p for p in payments}
        used_payment_ids: set = set(manual_map.values())

        # ── Construir matched ────────────────────────────────────────────────────
        matched = []
        solo_banco = []

        # 1. Cruces manuales registrados
        for mov in movements:
            if mov["id"] in manual_map:
                pay = payments_by_id.get(manual_map[mov["id"]]) or {}
                matched.append({**mov, "payment": pay, "match_type": "manual"})

        # 2. Auto-cruce para el resto
        for mov in movements:
            if mov["id"] in manual_map:
                continue

            payment = None
            match_type = None

            # Ronda 1: source_folio = folio del pago (más confiable — lo crea el bridge)
            sf = mov.get("source_folio") or ""
            if sf and sf in payments_by_folio:
                p = payments_by_folio[sf]
                if p["id"] not in used_payment_ids:
                    payment = p
                    match_type = "auto_folio"

            # Ronda 2: importe + fecha ±2 días (fallback para movimientos importados)
            if not payment:
                mov_amt = money(mov.get("amount"))
                mov_date = mov.get("movement_date") or ""
                for p in payments:
                    if p["id"] in used_payment_ids:
                        continue
                    if money(p.get("amount")) != mov_amt:
                        continue
                    p_date = p.get("payment_date") or ""
                    if mov_date and p_date and _DATE_RE.match(mov_date) and _DATE_RE.match(p_date):
                        diff = abs((date.fromisoformat(mov_date) - date.fromisoformat(p_date)).days)
                        if diff <= 2:
                            payment = p
                            match_type = "auto_importe_fecha"
                            break

            if payment:
                used_payment_ids.add(payment["id"])
                matched.append({**mov, "payment": payment, "match_type": match_type})
            else:
                solo_banco.append(mov)

        solo_billing = [p for p in payments if p["id"] not in used_payment_ids]

        return {
            "ok": True,
            "data": {
                "date_from": date_from,
                "date_to": date_to,
                "matched": matched,
                "solo_banco": solo_banco,
                "solo_billing": solo_billing,
                "stats": {
                    "total_matched": len(matched),
                    "total_solo_banco": len(solo_banco),
                    "total_solo_billing": len(solo_billing),
                    "importe_matched": round(sum(money(r.get("amount")) for r in matched), 2),
                    "importe_solo_banco": round(sum(money(r.get("amount")) for r in solo_banco), 2),
                    "importe_solo_billing": round(sum(money(r.get("amount")) for r in solo_billing), 2),
                },
            },
        }
