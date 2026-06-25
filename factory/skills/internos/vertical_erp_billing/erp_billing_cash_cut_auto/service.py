from __future__ import annotations
import importlib.util
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import SupabaseClient, money, resolve_billing_context, today_iso  # noqa: E402

_BILLING_SKILLS = Path(__file__).resolve().parents[1]


def _load_service(skill_dir: str, class_name: str):
    path = _BILLING_SKILLS / skill_dir / "service.py"
    spec = importlib.util.spec_from_file_location(f"_auto_{skill_dir}", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return getattr(m, class_name)


def _fmt(n: float) -> str:
    return f"${n:,.2f}"


def _send_telegram(token: str, chat_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


class ErpBillingCashCutAutoService:
    def ejecutar(self, context: dict) -> dict:
        ctx_result = resolve_billing_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]

        cut_date = str(context.get("cut_date") or today_iso())
        bot_token = os.getenv("FACTORY3_ADMIN_BOT_TOKEN") or str(context.get("bot_token") or "")
        chat_id = os.getenv("TELEGRAM_OWNER_CHAT_ID") or str(context.get("chat_id") or "")

        if not bot_token or not chat_id:
            return {"ok": False, "error": "FACTORY3_ADMIN_BOT_TOKEN y TELEGRAM_OWNER_CHAT_ID son requeridos"}

        # 1. ¿Ya existe un corte para hoy?
        billing_db = SupabaseClient(ctx)
        cortes_r = billing_db.rest_select(
            "billing_cash_cuts",
            filters={"cut_date": f"eq.{cut_date}"},
            select="id,folio,status,cut_date",
            limit=5,
        )
        cortes_hoy = cortes_r.get("data") or [] if cortes_r.get("ok") else []

        corte_created = False
        corte_folio = ""
        if not cortes_hoy:
            OpenService = _load_service("erp_billing_cash_cut_open", "ErpBillingCashCutOpenService")
            open_result = OpenService().ejecutar({
                **context,
                **ctx,
                "cut_date": cut_date,
                "dry_run": False,
                "notes": "Corte automático 7pm",
            })
            if not open_result.get("ok"):
                return open_result
            corte_created = True
            corte_folio = (open_result.get("data") or {}).get("cash_cut", {}).get("folio", "")
        else:
            corte_folio = cortes_hoy[0].get("folio", "")

        # 2. Datos del día
        DataService = _load_service("erp_billing_cash_cut_data", "ErpBillingCashCutDataService")
        data_result = DataService().ejecutar({**context, **ctx, "cut_date": cut_date})
        if not data_result.get("ok"):
            return data_result

        d = data_result["data"]
        t = d.get("totales") or {}

        # 3. Construir mensaje Telegram
        meses_es = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        dt = date.fromisoformat(cut_date)
        fecha_str = f"{dt.day} {meses_es[dt.month]} {dt.year}"

        lineas = [
            f"*Corte de Caja — {fecha_str}*",
            f"_{('creado automáticamente' if corte_created else 'corte existente')} • {corte_folio}_",
            "",
            f"*Ventas del día:* {_fmt(t.get('total_ventas_dia', 0))}",
            f"*Cobrado hoy:* {_fmt(t.get('total_pagos_hoy', 0))}",
            f"*CXC hoy:* {_fmt(t.get('cxc_dia', 0))}",
            f"*CXC anteriores:* {_fmt(t.get('total_cxc_anteriores', 0))}",
        ]

        por_confirmar = t.get("total_por_confirmar", 0)
        if por_confirmar > 0:
            lineas.append(f"*Por confirmar:* {_fmt(por_confirmar)} ⚠️")

        # Desglose por método de pago
        pagos = d.get("pagos_hoy") or []
        by_method: dict = {}
        for p in pagos:
            m = str(p.get("payment_method") or "otro").replace("_", " ").title()
            by_method[m] = by_method.get(m, 0) + money(p.get("amount"))
        if by_method:
            lineas.append("")
            lineas.append("*Por método:*")
            for m, amt in sorted(by_method.items()):
                lineas.append(f"  {m}: {_fmt(amt)}")

        texto = "\n".join(lineas)

        # 4. Enviar
        tg_result = _send_telegram(bot_token, chat_id, texto)

        return {
            "ok": True,
            "data": {
                "cut_date": cut_date,
                "corte_folio": corte_folio,
                "corte_created": corte_created,
                "telegram_sent": bool(tg_result.get("ok")),
                "telegram_error": tg_result.get("error") if not tg_result.get("ok") else None,
                "totales": t,
            },
        }
