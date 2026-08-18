"""Handler WhatsApp para captura de pedidos de ventas — canal-agnostic.

Recibe {type, body, from_phone, usuario_empresa_id/empresa_id, dry_run} y
devuelve {reply}. La maquina de estados se persiste en public.bot_states con
chat_id = pedido_wabiz_{company_id}_{from_phone}.

No hardcodea empresa/schema: company_id viene del contexto (login por codigo
de acceso en wabiz_access_codes) y el schema se resuelve via
erp_project_context_resolve, igual que erp_ventas_pedido_create.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from factory.engine import SupabaseClient

_MAX_LIST = 8
_MAX_HISTORY = 12
_PROGRESS_STEPS = {
    "client", "client_confirm_new", "client_pick",
    "fecha", "fecha_manual",
    "product", "product_pick", "quantity", "price", "lot_pick",
    "payment_method", "confirm",
}
_PAYMENT_METHODS = [
    ("cash", "Contado"),
    ("credit", "Crédito"),
    ("transfer", "Transferencia"),
    ("check", "Cheque"),
    ("other", "Otro"),
]

_AYUDA = (
    "*Pedidos por WhatsApp*\n\n"
    "Escribe *pedido* para iniciar uno nuevo.\n\n"
    "*Durante la captura:*\n"
    "• Nombre del cliente o producto, para buscar\n"
    "• */claves* — ver productos clave numerados\n"
    "• Un numero (ej: 3) — selecciona ese producto clave directo\n"
    "• *fin* — cerrar la lista de productos\n"
    "• *cambiar N* — borra la partida N para volver a capturarla\n"
    "• */ver* — ver lo capturado hasta ahora\n"
    "• */r* — regresar a la pregunta anterior\n"
    "• *cancelar* — abortar en cualquier momento"
)

_EDIT_RE = re.compile(r"^(?:cambiar|editar)\s+(\d+)$")
_FECHA_RE = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$")
_WEEKDAY_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
_MONTH_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class ErpVentasWabizPedidoHandlerService:
    def ejecutar(self, context: dict) -> dict:
        from_phone = str(context.get("from_phone") or "").strip()
        if not from_phone:
            return {"ok": False, "error": "from_phone requerido"}

        company_id = str(context.get("usuario_empresa_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": True, "data": {"reply": "Tu numero no esta asociado a ninguna empresa. Contacta al administrador."}}

        msg_type = context.get("type", "text")
        if msg_type == "interactive":
            # respuesta de boton: el id llega en "body" (ver wabiz_webhook_parse), se enruta como texto
            msg_type = "text"
        body = str(context.get("body") or "").strip()
        dry_run = context.get("dry_run", True)

        cfg_result = self._cfg(context, company_id)
        if not cfg_result.get("ok"):
            return {"ok": True, "data": {"reply": f"⚠️ Configuracion incompleta: {cfg_result.get('error')}"}}
        cfg = cfg_result["data"]

        chat_id = f"pedido_wabiz_{company_id}_{from_phone}"
        state = self._load_state(chat_id)
        step = state.get("step", "idle")
        text_lower = body.lower().strip()

        if msg_type != "text":
            reply, new_state = "Por ahora solo puedo leer texto para pedidos.", state
        elif text_lower in ("cancelar", "/cancelar", "cancel", "/cancel") and step != "idle":
            reply, new_state = "Pedido cancelado.", {}
        elif text_lower in ("ayuda", "/ayuda"):
            reply, new_state = self._ayuda(cfg), state
        elif text_lower in ("/ver", "ver"):
            reply, new_state = (self._build_progress(state) if step in _PROGRESS_STEPS
                                 else "No hay ningun pedido en progreso. Escribe *pedido* para iniciar uno."), state
        elif text_lower == "/r":
            reply, new_state = self._handle_back(state) if step in _PROGRESS_STEPS else (
                "No hay ningun pedido en progreso. Escribe *pedido* para iniciar uno.", state
            )
        elif step == "idle":
            reply, new_state = self._handle_idle(text_lower)
        elif step in _PROGRESS_STEPS:
            history = self._with_history(state)
            reply, new_state = self._dispatch(step, body, text_lower, cfg, state, dry_run)
            new_state = {**new_state, "_history": history} if new_state else new_state
        else:
            reply, new_state = "Escribe *pedido* para iniciar uno nuevo.", {}

        if not dry_run:
            self._save_state(chat_id, new_state)

        if isinstance(reply, dict):
            return {"ok": True, "data": {"interactive": reply}}
        return {"ok": True, "data": {"reply": reply}}

    def _dispatch(self, step: str, body: str, text_lower: str, cfg: dict, state: dict, dry_run: bool) -> tuple[str, dict]:
        if step == "client":
            return self._handle_client(body, cfg, state)
        if step == "client_confirm_new":
            return self._handle_client_confirm_new(text_lower, state, cfg, dry_run)
        if step == "client_pick":
            return self._handle_client_pick(body, state)
        if step == "fecha":
            return self._handle_fecha(body, text_lower, state)
        if step == "fecha_manual":
            return self._handle_fecha_manual(body, state)
        if step == "product":
            return self._handle_product(body, text_lower, cfg, state)
        if step == "product_pick":
            return self._handle_product_pick(body, state)
        if step == "quantity":
            return self._handle_quantity(body, state)
        if step == "price":
            return self._handle_price(body, state, cfg)
        if step == "lot_pick":
            return self._handle_lot_pick(body, state)
        if step == "payment_method":
            return self._handle_payment_method(body, state)
        if step == "confirm":
            return self._handle_confirm(text_lower, state, cfg, dry_run)
        return "Escribe *pedido* para iniciar uno nuevo.", {}

    # ── PASOS ─────────────────────────────────────────────────────────────────

    def _handle_idle(self, text_lower: str) -> tuple[str, dict]:
        if text_lower in ("pedido", "/pedido"):
            return "\U0001f9fe Nuevo pedido\n¿Cliente? Escribe el nombre.", {"step": "client", "items": []}
        return "Escribe *pedido* para iniciar uno nuevo, o *ayuda*.", {}

    def _handle_client(self, body: str, cfg: dict, state: dict) -> tuple[str, dict]:
        text = body.strip()
        if not text:
            return "Escribe el nombre del cliente.", state
        matches = self._search_customers(cfg, text)
        if len(matches) == 1:
            c = matches[0]
            base = {**state, "customer_id": c["id"], "customer_name": c["party_name"]}
            return self._start_fecha_step(base, prefix=f"Cliente: {c['party_name']} ✓")
        if len(matches) > 1:
            listed = matches[:_MAX_LIST]
            lines = [f"{i}. {c['party_name']}" for i, c in enumerate(listed, start=1)]
            new_state = {
                **state,
                "step": "client_pick",
                "client_candidates": [{"id": c["id"], "party_name": c["party_name"]} for c in listed],
            }
            return "Encontre varios clientes:\n" + "\n".join(lines) + "\n\nEscribe el numero.", new_state
        new_state = {**state, "step": "client_confirm_new", "client_candidate_name": text}
        return f'No encontre clientes con "{text}". ¿Creo cliente nuevo "{text}"? (si/no)', new_state

    def _handle_client_confirm_new(self, text_lower: str, state: dict, cfg: dict, dry_run: bool) -> tuple[str, dict]:
        if text_lower in ("si", "sí", "s", "yes"):
            name = state.get("client_candidate_name", "")
            res = self._get_or_create_customer(cfg, name, dry_run)
            if not res.get("ok"):
                return f"⚠️ No pude crear el cliente: {res.get('error')}", {}
            customer = (res.get("data") or {}).get("customer") or {}
            customer_id = customer.get("id") or ("cliente-dryrun" if dry_run else None)
            if not customer_id:
                return "⚠️ No pude crear el cliente. Intenta de nuevo.", {}
            base = {**state, "customer_id": customer_id, "customer_name": name}
            return self._start_fecha_step(base, prefix=f"Cliente nuevo: {name} ✓")
        if text_lower in ("no", "n"):
            new_state = {**state, "step": "client"}
            return "Ok, escribe otro nombre de cliente.", new_state
        return "Responde *si* o *no*.", state

    def _handle_client_pick(self, body: str, state: dict) -> tuple[str, dict]:
        candidates = state.get("client_candidates") or []
        idx = self._parse_index(body)
        if idx is None or idx < 1 or idx > len(candidates):
            return f"Escribe un numero del 1 al {len(candidates)}.", state
        c = candidates[idx - 1]
        base = {k: v for k, v in state.items() if k != "client_candidates"}
        base = {**base, "customer_id": c["id"], "customer_name": c["party_name"]}
        return self._start_fecha_step(base, prefix=f"Cliente: {c['party_name']} ✓")

    def _handle_fecha(self, body: str, text_lower: str, state: dict) -> tuple[str, dict]:
        if text_lower == "fecha_1":
            return self._fecha_selected(state, state.get("fecha_opcion_1"))
        if text_lower == "fecha_2":
            return self._fecha_selected(state, state.get("fecha_opcion_2"))
        if text_lower in ("fecha_3", "otra fecha", "otra"):
            new_state = {**state, "step": "fecha_manual"}
            return "Escribe la fecha de entrega (dd/mm/aa).", new_state
        parsed = self._parse_fecha_text(body)
        if parsed:
            return self._fecha_selected(state, parsed)
        return "Elige una opcion de fecha, o escribe la fecha (dd/mm/aa).", state

    def _handle_fecha_manual(self, body: str, state: dict) -> tuple[str, dict]:
        parsed = self._parse_fecha_text(body)
        if not parsed:
            return "Fecha invalida. Escribe dd/mm/aa (ej: 15/08/26).", state
        return self._fecha_selected(state, parsed)

    def _fecha_selected(self, state: dict, iso_date: str) -> tuple[str, dict]:
        new_state = {k: v for k, v in state.items() if k not in ("fecha_opcion_1", "fecha_opcion_2")}
        new_state = {**new_state, "step": "product", "due_date": iso_date}
        return f"Entrega: {self._fmt_date_label(date.fromisoformat(iso_date))} ✓\n\n{self._product_prompt()}", new_state

    def _handle_product(self, body: str, text_lower: str, cfg: dict, state: dict) -> tuple[str, dict]:
        text = body.strip()
        text_bare = text_lower.lstrip("/")

        edit_match = _EDIT_RE.match(text_lower)
        if edit_match:
            return self._edit_item(int(edit_match.group(1)), state, back_step="product")

        if text_bare == "fin":
            items = state.get("items") or []
            if not items:
                return "Todavia no agregas ningun producto.", state
            new_state = {**state, "step": "payment_method"}
            return self._payment_method_prompt(), new_state

        if text_bare == "claves":
            products = self._search_key_products(cfg)
            if not products:
                return "No hay productos clave configurados. Escribe el nombre del producto.", state
            return self._key_products_list(products), state

        if text.isdigit():
            products = self._search_key_products(cfg)
            idx = int(text)
            if 1 <= idx <= len(products):
                p = products[idx - 1]
                new_state = {
                    **state,
                    "step": "quantity",
                    "pending_product": {"id": p["id"], "product_name": p["product_name"], "unit": p.get("unit")},
                }
                return f"Producto: {p['product_name']} ✓ ¿Cantidad?", new_state
            return f"No hay producto clave con el numero {idx}. Escribe */claves* para ver la lista.", state

        if not text:
            return self._product_prompt(), state

        matches = self._search_products(cfg, text)
        if len(matches) == 1:
            p = matches[0]
            new_state = {
                **state,
                "step": "quantity",
                "pending_product": {"id": p["id"], "product_name": p["product_name"], "unit": p.get("unit")},
            }
            return f"Producto: {p['product_name']} ✓ ¿Cantidad?", new_state
        if len(matches) > 1:
            listed = matches[:_MAX_LIST]
            lines = [f"{i}. {p['product_name']}" for i, p in enumerate(listed, start=1)]
            new_state = {
                **state,
                "step": "product_pick",
                "product_candidates": [
                    {"id": p["id"], "product_name": p["product_name"], "unit": p.get("unit")} for p in listed
                ],
            }
            return "Encontre varios productos:\n" + "\n".join(lines) + "\n\nEscribe el numero.", new_state
        return f'No encontre productos con "{text}". Intenta otro nombre o escribe /claves.', state

    def _handle_product_pick(self, body: str, state: dict) -> tuple[str, dict]:
        candidates = state.get("product_candidates") or []
        idx = self._parse_index(body)
        if idx is None or idx < 1 or idx > len(candidates):
            return f"Escribe un numero del 1 al {len(candidates)}.", state
        p = candidates[idx - 1]
        new_state = {k: v for k, v in state.items() if k != "product_candidates"}
        new_state = {**new_state, "step": "quantity", "pending_product": p}
        return f"Producto: {p['product_name']} ✓ ¿Cantidad?", new_state

    def _handle_quantity(self, body: str, state: dict) -> tuple[str, dict]:
        qty = self._parse_number(body)
        if qty is None or qty <= 0:
            return "Escribe una cantidad valida (ej: 20).", state
        new_state = {**state, "step": "price", "pending_qty": qty}
        return f"Cantidad: {self._fmt_num(qty)} ✓ ¿Precio unitario (con IVA)?", new_state

    def _handle_price(self, body: str, state: dict, cfg: dict) -> tuple[str, dict]:
        price = self._parse_number(body)
        if price is None or price < 0:
            return "Escribe un precio valido (ej: 214.6).", state
        product = state.get("pending_product") or {}
        qty = state.get("pending_qty") or 0
        lots = self._lot_options(cfg, product.get("id"))
        if len(lots) > 1:
            new_state = {**state, "step": "lot_pick", "pending_price": price, "lot_candidates": lots}
            return self._lot_pick_prompt(product, lots), new_state
        lot_code = lots[0]["lot_code"] if lots else None
        return self._finish_item(product, qty, price, lot_code, state)

    def _handle_lot_pick(self, body: str, state: dict) -> tuple[str, dict]:
        candidates = state.get("lot_candidates") or []
        idx = self._parse_index(body)
        if idx is None or idx < 1 or idx > len(candidates):
            return f"Escribe un numero del 1 al {len(candidates)}.", state
        lot = candidates[idx - 1]
        product = state.get("pending_product") or {}
        qty = state.get("pending_qty") or 0
        price = state.get("pending_price") or 0
        return self._finish_item(product, qty, price, lot.get("lot_code"), state)

    def _finish_item(self, product: dict, qty: float, price: float, lot_code: str | None, state: dict) -> tuple[str, dict]:
        item = {
            "product_id": product.get("id"),
            "product_name": product.get("product_name"),
            "unit": product.get("unit"),
            "quantity": qty,
            "unit_price_inc_vat": price,
            "lot_code": lot_code,
        }
        items = list(state.get("items") or [])
        items.append(item)
        new_state = {
            k: v for k, v in state.items()
            if k not in ("pending_product", "pending_qty", "pending_price", "lot_candidates")
        }
        new_state = {**new_state, "step": "product", "items": items}
        line_total = round(qty * price, 2)
        lot_suffix = f" (lote {lot_code})" if lot_code else ""
        reply = (
            f"✅ {self._fmt_num(qty)} x {product.get('product_name')}{lot_suffix} @ ${price:,.2f} = ${line_total:,.2f}\n\n"
            '¿Otro producto? Escribe nombre/#/clave o "fin" para terminar.'
        )
        return reply, new_state

    def _handle_payment_method(self, body: str, state: dict) -> tuple[str, dict]:
        idx = self._parse_index(body)
        if idx is None or idx < 1 or idx > len(_PAYMENT_METHODS):
            return f"Escribe un numero del 1 al {len(_PAYMENT_METHODS)}.", state
        value, label = _PAYMENT_METHODS[idx - 1]
        new_state = {**state, "step": "confirm", "payment_method": value, "payment_method_label": label}
        return self._build_summary(state.get("items") or [], new_state), new_state

    def _handle_confirm(self, text_lower: str, state: dict, cfg: dict, dry_run: bool) -> tuple[str, dict]:
        edit_match = _EDIT_RE.match(text_lower)
        if edit_match:
            return self._edit_item(int(edit_match.group(1)), state, back_step="product")
        if text_lower in ("cancelar", "no", "n"):
            return "Pedido cancelado.", {}
        if text_lower not in ("confirmar", "si", "sí", "yes"):
            return 'Escribe *confirmar* para guardar, *cambiar N* para corregir una partida, o *cancelar*.', state
        items = state.get("items") or []
        payload_items = [
            {
                "product_id": it["product_id"],
                "description": it["product_name"],
                "quantity": it["quantity"],
                "unit": it.get("unit") or "pieza",
                "unit_price_inc_vat": it["unit_price_inc_vat"],
                "lot_code": it.get("lot_code"),
            }
            for it in items
        ]
        res = self._create_pedido(
            cfg, state.get("customer_id"), state.get("customer_name"), payload_items,
            state.get("due_date"), state.get("payment_method"), dry_run,
        )
        if not res.get("ok"):
            return f"⚠️ No pude guardar el pedido: {res.get('error')}", state
        pedido = (res.get("data") or {}).get("pedido") or {}
        folio = pedido.get("folio", "?")
        total = pedido.get("total", 0)
        try:
            total_fmt = f"{float(total):,.2f}"
        except (TypeError, ValueError):
            total_fmt = str(total)
        return f"✅ Pedido *{folio}* guardado — Total ${total_fmt}", {}

    def _edit_item(self, idx: int, state: dict, back_step: str) -> tuple[str, dict]:
        items = list(state.get("items") or [])
        if idx < 1 or idx > len(items):
            return f"No existe la partida {idx}. Escribe */ver* para ver las partidas actuales.", state
        removed = items.pop(idx - 1)
        new_state = {**state, "items": items, "step": back_step}
        return (
            f"Partida {idx} eliminada ({self._fmt_num(removed['quantity'])} x {removed['product_name']}).\n\n"
            f"{self._product_prompt()}"
        ), new_state

    # ── FECHA DE ENTREGA ─────────────────────────────────────────────────────

    def _next_business_dates(self, n: int) -> list[date]:
        """Siguientes n fechas saltando domingo (dia laborable = todo menos domingo)."""
        dates: list[date] = []
        d = date.today() + timedelta(days=1)
        while len(dates) < n:
            if d.weekday() != 6:  # 6 = domingo
                dates.append(d)
            d += timedelta(days=1)
        return dates

    def _fmt_date_label(self, d: date) -> str:
        return f"{_WEEKDAY_ES[d.weekday()]} {d.day} {_MONTH_ES[d.month - 1]}"

    def _parse_fecha_text(self, text: str) -> str | None:
        match = _FECHA_RE.match(text.strip())
        if not match:
            return None
        d_str, mo_str, y_str = match.groups()
        try:
            year = int(y_str)
            if year < 100:
                year += 2000
            return date(year, int(mo_str), int(d_str)).isoformat()
        except (TypeError, ValueError):
            return None

    def _fecha_buttons(self, d1: date, d2: date) -> dict:
        return {
            "body": "¿Fecha prometida de entrega?",
            "interactive_type": "button",
            "buttons": [
                {"id": "fecha_1", "title": self._fmt_date_label(d1)},
                {"id": "fecha_2", "title": self._fmt_date_label(d2)},
                {"id": "fecha_3", "title": "Otra fecha"},
            ],
        }

    def _start_fecha_step(self, state: dict, prefix: str = "") -> tuple[dict, dict]:
        d1, d2 = self._next_business_dates(2)
        new_state = {
            **state,
            "step": "fecha",
            "fecha_opcion_1": d1.isoformat(),
            "fecha_opcion_2": d2.isoformat(),
        }
        interactive = self._fecha_buttons(d1, d2)
        if prefix:
            interactive = {**interactive, "body": f"{prefix}\n\n{interactive['body']}"}
        return interactive, new_state

    # ── TEXTOS ────────────────────────────────────────────────────────────────

    def _product_prompt(self) -> str:
        return "¿Producto? Escribe nombre, numero de clave o /claves para ver la lista."

    def _key_products_list(self, products: list[dict]) -> str:
        lines = [f"{i}. {p['product_name']}" for i, p in enumerate(products, start=1)]
        return "Productos clave:\n" + "\n".join(lines) + "\n\nEscribe el numero."

    def _lot_pick_prompt(self, product: dict, lots: list[dict]) -> str:
        lines = [f"{i}. {lot.get('label')}" for i, lot in enumerate(lots, start=1)]
        return (
            f"Lotes disponibles de {product.get('product_name')}:\n" + "\n".join(lines)
            + "\n\nEscribe el numero de lote."
        )

    def _payment_method_prompt(self) -> str:
        lines = [f"{i}. {label}" for i, (_, label) in enumerate(_PAYMENT_METHODS, start=1)]
        return "¿Forma de pago?\n" + "\n".join(lines) + "\n\nEscribe el numero."

    def _ayuda(self, cfg: dict) -> str:
        products = self._search_key_products(cfg)
        if not products:
            return _AYUDA
        return _AYUDA + "\n\n" + self._key_products_list(products)

    def _build_summary(self, items: list[dict], state: dict) -> str:
        lines = []
        total_inc = 0.0
        for i, it in enumerate(items, start=1):
            line_total = round(float(it["quantity"]) * float(it["unit_price_inc_vat"]), 2)
            total_inc += line_total
            lines.append(f"{i}. {self._fmt_num(it['quantity'])} x {it['product_name']} = ${line_total:,.2f}")
        customer_name = state.get("customer_name", "")
        entrega = self._fmt_due_date(state.get("due_date"))
        pago = state.get("payment_method_label")
        pago_line = f"Forma de pago: {pago}\n" if pago else ""
        return (
            f"\U0001f4cb Resumen — {customer_name}\n"
            f"Entrega: {entrega}\n"
            f"{pago_line}"
            + "\n".join(lines)
            + f"\n\nTotal (IVA incluido): ${total_inc:,.2f}\n\n"
            'Escribe *confirmar* para guardar, *cambiar N* para corregir una partida, o *cancelar*.'
        )

    def _fmt_due_date(self, iso_date: str | None) -> str:
        if not iso_date:
            return "(sin definir)"
        try:
            return self._fmt_date_label(date.fromisoformat(iso_date))
        except (TypeError, ValueError):
            return iso_date

    def _build_progress(self, state: dict) -> str:
        items = state.get("items") or []
        customer_name = state.get("customer_name")
        lines = [f"Cliente: {customer_name}" if customer_name else "Cliente: (sin definir todavia)"]
        if state.get("due_date"):
            lines.append(f"Entrega: {self._fmt_due_date(state.get('due_date'))}")
        if items:
            lines.append("\nProductos capturados:")
            total = 0.0
            for i, it in enumerate(items, start=1):
                line_total = round(float(it["quantity"]) * float(it["unit_price_inc_vat"]), 2)
                total += line_total
                lines.append(f"{i}. {self._fmt_num(it['quantity'])} x {it['product_name']} = ${line_total:,.2f}")
            lines.append(f"\nTotal hasta ahora: ${total:,.2f}")
        else:
            lines.append("\nAun no hay productos capturados.")
        step = state.get("step")
        if step == "quantity":
            p = state.get("pending_product") or {}
            lines.append(f"\nFalta: cantidad de {p.get('product_name')}.")
        elif step == "price":
            p = state.get("pending_product") or {}
            qty = state.get("pending_qty")
            lines.append(f"\nFalta: precio de {self._fmt_num(qty)} x {p.get('product_name')}.")
        elif step == "lot_pick":
            p = state.get("pending_product") or {}
            lines.append(f"\nFalta: elegir lote de {p.get('product_name')}.")
        elif step == "payment_method":
            lines.append("\nFalta: forma de pago.")
        elif step in ("client", "client_confirm_new", "client_pick"):
            lines.append("\nFalta: definir el cliente.")
        elif step == "confirm":
            lines.append("\nListo para *confirmar*.")
        return "\n".join(lines)

    def _reprompt(self, state: dict) -> str | dict:
        step = state.get("step")
        if step == "client":
            return "¿Cliente? Escribe el nombre."
        if step == "client_confirm_new":
            name = state.get("client_candidate_name", "")
            return f'No encontre clientes con "{name}". ¿Creo cliente nuevo "{name}"? (si/no)'
        if step == "client_pick":
            candidates = state.get("client_candidates") or []
            lines = [f"{i}. {c['party_name']}" for i, c in enumerate(candidates, start=1)]
            return "Encontre varios clientes:\n" + "\n".join(lines) + "\n\nEscribe el numero."
        if step == "fecha":
            try:
                d1 = date.fromisoformat(state.get("fecha_opcion_1"))
                d2 = date.fromisoformat(state.get("fecha_opcion_2"))
                return self._fecha_buttons(d1, d2)
            except (TypeError, ValueError):
                return "¿Fecha prometida de entrega? Escribe dd/mm/aa."
        if step == "fecha_manual":
            return "Escribe la fecha de entrega (dd/mm/aa)."
        if step == "product":
            return self._product_prompt()
        if step == "product_pick":
            candidates = state.get("product_candidates") or []
            lines = [f"{i}. {c['product_name']}" for i, c in enumerate(candidates, start=1)]
            return "Escribe el numero:\n" + "\n".join(lines)
        if step == "quantity":
            p = state.get("pending_product") or {}
            return f"Producto: {p.get('product_name')} ✓ ¿Cantidad?"
        if step == "price":
            p = state.get("pending_product") or {}
            qty = state.get("pending_qty")
            return f"Cantidad: {self._fmt_num(qty)} ✓ ¿Precio unitario (con IVA)?"
        if step == "lot_pick":
            product = state.get("pending_product") or {}
            candidates = state.get("lot_candidates") or []
            return self._lot_pick_prompt(product, candidates)
        if step == "payment_method":
            return self._payment_method_prompt()
        if step == "confirm":
            return self._build_summary(state.get("items") or [], state)
        return "Escribe *pedido* para iniciar uno nuevo."

    def _handle_back(self, state: dict) -> tuple[str, dict]:
        history = list(state.get("_history") or [])
        if not history:
            return "No hay nada a que regresar.", state
        previous = history.pop()
        previous = {**previous, "_history": history}
        return self._reprompt(previous), previous

    # ── HISTORIAL ─────────────────────────────────────────────────────────────

    def _with_history(self, state: dict) -> list[dict]:
        history = list(state.get("_history") or [])
        history.append({k: v for k, v in state.items() if k != "_history"})
        return history[-_MAX_HISTORY:]

    # ── BUSQUEDAS ─────────────────────────────────────────────────────────────

    def _search_customers(self, cfg: dict, text: str) -> list[dict]:
        safe = text.replace(",", " ").replace("%", "")
        db = SupabaseClient(self._inventory_context(cfg))
        res = db.rest_select(
            "erp_parties",
            filters={"party_name": f"ilike.%{safe}%", "party_type": "in.(customer,both)", "active": "eq.true"},
            select="id,folio,party_name",
            order="party_name.asc",
            limit=20,
        )
        return (res.get("data") or []) if res.get("ok") else []

    def _search_products(self, cfg: dict, text: str) -> list[dict]:
        safe = text.replace(",", " ").replace("%", "")
        db = SupabaseClient(self._inventory_context(cfg))
        res = db.rest_select(
            "erp_products",
            filters={"product_name": f"ilike.%{safe}%", "active": "eq.true"},
            select="id,folio,product_name,unit,sku",
            order="product_name.asc",
            limit=20,
        )
        return (res.get("data") or []) if res.get("ok") else []

    def _search_key_products(self, cfg: dict) -> list[dict]:
        db = SupabaseClient(self._inventory_context(cfg))
        res = db.rest_select(
            "erp_products",
            filters={"active": "eq.true", "is_key_product": "eq.true"},
            select="id,folio,product_name,unit,sku",
            order="product_name.asc",
            limit=_MAX_LIST,
        )
        return (res.get("data") or []) if res.get("ok") else []

    # ── SKILLS EXTERNOS ───────────────────────────────────────────────────────

    def _cfg(self, context: dict, company_id: str) -> dict:
        resolve_context = {**context, "company_id": company_id, "module_code": "ventas"}
        res = _runner().run("vertical_erp/erp_project_context_resolve", resolve_context)
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error") or "contexto ERP de ventas incompleto"}
        data = res.get("data") or {}
        module_projects = data.get("module_projects") if isinstance(data.get("module_projects"), dict) else {}
        cfg = {
            "empresa_id": data.get("empresa_id") or data.get("company_id"),
            "schema_ventas": data.get("sales_schema") or data.get("schema"),
            "schema_inventario": data.get("inventory_schema"),
            "project_ventas": data.get("project_code"),
            "project_inv": module_projects.get("inventario"),
            "module_ventas": data.get("module_code") or "ventas",
            "module_inv": "inventario",
        }
        missing = [key for key, value in cfg.items() if not value]
        if missing:
            return {"ok": False, "error": f"contexto ERP de ventas incompleto: {', '.join(missing)}"}
        return {"ok": True, "data": cfg}

    def _inventory_context(self, cfg: dict) -> dict:
        return {
            "schema": cfg["schema_inventario"],
            "company_id": cfg["empresa_id"],
            "empresa_id": cfg["empresa_id"],
            "project_code": cfg["project_inv"],
            "module_code": cfg["module_inv"],
        }

    def _get_or_create_customer(self, cfg: dict, customer_name: str, dry_run: bool) -> dict:
        payload = {**self._inventory_context(cfg), "customer_name": customer_name, "dry_run": dry_run}
        return _runner().run("vertical_erp_ventas/erp_ventas_customer_get_or_create", payload)

    def _create_pedido(
        self, cfg: dict, customer_id: str, customer_name: str, items: list[dict],
        due_date: str | None, payment_method: str | None, dry_run: bool,
    ) -> dict:
        payload = {
            "company_id": cfg["empresa_id"],
            "empresa_id": cfg["empresa_id"],
            "module_code": "ventas",
            "customer_id": customer_id,
            "customer_name": customer_name,
            "items": items,
            "due_date": due_date,
            "payment_method": payment_method,
            "dry_run": dry_run,
        }
        return _runner().run("vertical_erp_ventas/erp_ventas_pedido_create", payload)

    def _lot_options(self, cfg: dict, product_id: str | None) -> list[dict]:
        if not product_id:
            return []
        res = _runner().run(
            "vertical_erp_inventory/erp_inventory_lot_options",
            {**self._inventory_context(cfg), "product_id": product_id},
        )
        if not res.get("ok"):
            return []
        return (res.get("data") or {}).get("lots") or []

    # ── ESTADO ────────────────────────────────────────────────────────────────

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

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _parse_index(self, text: str) -> int | None:
        try:
            return int(text.strip())
        except (TypeError, ValueError):
            return None

    def _parse_number(self, text: str) -> float | None:
        cleaned = text.strip().replace("$", "").replace(",", "")
        try:
            return float(cleaned)
        except (TypeError, ValueError):
            return None

    def _fmt_num(self, value: float) -> str:
        try:
            if float(value).is_integer():
                return str(int(value))
            return f"{value:g}"
        except (TypeError, ValueError):
            return str(value)
