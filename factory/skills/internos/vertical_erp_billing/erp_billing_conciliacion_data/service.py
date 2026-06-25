from __future__ import annotations
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, blank, money, resolve_billing_context  # noqa: E402


def _banks_ctx(ctx: dict, banks_schema: str) -> dict:
    return {**ctx, "schema": banks_schema, "company_id": ctx.get("company_id") or ctx.get("empresa_id")}


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

        # ── Pagos de cobranza (billing schema) ─────────────────────────────────
        billing_db = SupabaseClient(ctx)
        pay_r = billing_db.rest_select(
            "billing_payments",
            filters={},
            select="id,folio,customer_name,amount,payment_date,payment_method,confirmation_status,tracking_key,status",
            limit=500,
            order="payment_date.desc",
        )
        all_payments = pay_r.get("data") or [] if pay_r.get("ok") else []
        payments = [
            p for p in all_payments
            if date_from <= (p.get("payment_date") or "") <= date_to
            and p.get("status") != "cancelado"
        ]

        # ── Movimientos bancarios (banks schema) ────────────────────────────────
        banks_db = SupabaseClient(_banks_ctx(ctx, banks_schema))
        mov_filters: dict = {"movement_type": "eq.entrada", "source_type": "eq.pago"}
        if account_id:
            mov_filters["account_id"] = f"eq.{account_id}"

        mov_r = banks_db.rest_select(
            "banks_movements",
            filters=mov_filters,
            select="id,folio,account_id,account_folio,amount,movement_date,source_folio,source_id,clave_rastreo,reconciliation_status,notes",
            limit=500,
            order="movement_date.desc",
        )
        all_movements = mov_r.get("data") or [] if mov_r.get("ok") else []
        movements = [
            m for m in all_movements
            if date_from <= (m.get("movement_date") or "") <= date_to
        ]

        # ── Cruces manuales existentes ──────────────────────────────────────────
        manual_matched_mov_ids: set = set()
        manual_matched_pay_ids: set = set()
        try:
            mc_r = billing_db.rest_select(
                "billing_conciliacion_matches",
                filters={"status": "eq.activo"},
                select="movement_id,payment_id,match_type",
                limit=500,
            )
            if mc_r.get("ok"):
                for mm in (mc_r.get("data") or []):
                    manual_matched_mov_ids.add(mm.get("movement_id"))
                    manual_matched_pay_ids.add(mm.get("payment_id"))
        except Exception:
            pass

        # ── Índices ─────────────────────────────────────────────────────────────
        payments_by_folio = {p["folio"]: p for p in payments if p.get("folio")}
        payments_by_tracking = {p["tracking_key"]: p for p in payments if p.get("tracking_key")}
        payments_by_id = {p["id"]: p for p in payments}
        used_payment_ids: set = set(manual_matched_pay_ids)

        # ── Auto-cruce ──────────────────────────────────────────────────────────
        matched = []
        solo_banco = []

        # Primero los cruces manuales ya registrados
        for mid in manual_matched_mov_ids:
            mov = next((m for m in movements if m["id"] == mid), None)
            pay = payments_by_id.get(list(manual_matched_pay_ids)[list(manual_matched_mov_ids).index(mid)] if mid in manual_matched_mov_ids else "")
            if mov:
                matched.append({**mov, "payment": pay or {}, "match_type": "manual"})

        for mov in movements:
            if mov["id"] in manual_matched_mov_ids:
                continue

            payment = None
            match_type = None

            # 1. source_folio → payment folio
            sf = mov.get("source_folio")
            if sf and sf in payments_by_folio:
                p = payments_by_folio[sf]
                if p["id"] not in used_payment_ids:
                    payment = p
                    match_type = "auto_folio"

            # 2. clave_rastreo → tracking_key
            if not payment:
                cr = mov.get("clave_rastreo")
                if cr and cr in payments_by_tracking:
                    p = payments_by_tracking[cr]
                    if p["id"] not in used_payment_ids:
                        payment = p
                        match_type = "auto_clave"

            # 3. Importe + fecha (±2 días)
            if not payment:
                mov_amt = money(mov.get("amount"))
                mov_date = mov.get("movement_date") or ""
                for p in payments:
                    if p["id"] in used_payment_ids:
                        continue
                    if money(p.get("amount")) != mov_amt:
                        continue
                    p_date = p.get("payment_date") or ""
                    if mov_date and p_date:
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
