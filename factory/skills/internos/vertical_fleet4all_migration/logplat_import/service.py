from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any

from factory.engine import SupabaseClient


class LogplatImportService:
    def ejecutar(self, context: dict) -> dict:
        source_schema = str(context.get("source_schema") or "").strip()
        target_schema = str(context.get("target_schema") or context.get("schema") or "").strip()
        target_empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip().upper()
        if not source_schema:
            return {"ok": False, "error": "source_schema requerido en context"}
        if not target_schema:
            return {"ok": False, "error": "target_schema/schema requerido en context"}
        if not target_empresa_id:
            return {"ok": False, "error": "empresa_id/company_id requerido en context"}

        limit = int(context.get("limit") or 10000)
        source = SupabaseClient({**context, "schema": source_schema})
        target = SupabaseClient({**context, "schema": target_schema})

        loaded = self._load_source(source, limit)
        if not loaded.get("ok"):
            return loaded

        source_rows = loaded["data"]
        mapped = self._map_all(source_rows, target_empresa_id)
        preview = self._preview(source_rows, mapped)
        warnings = mapped.get("warnings", [])

        if context.get("dry_run", True):
            return {
                "ok": True,
                "message": "dry_run: no se escribio en fleet4all",
                "data": {**preview, "warnings": warnings},
            }

        if not context.get("confirm"):
            return {"ok": False, "error": "confirm=true requerido para importar datos reales"}

        written = self._write_target(target, mapped["rows"])
        if not written.get("ok"):
            return written
        return {"ok": True, "data": {**preview, "written": written["data"], "warnings": warnings}}

    def _load_source(self, source: SupabaseClient, limit: int) -> dict:
        tables = ("viajes", "gastos", "pagos", "cuentas_por_cobrar", "viaje_docs")
        data = {}
        for table in tables:
            res = source.rest_select(table, select="*", limit=limit)
            if not res.get("ok"):
                return {"ok": False, "error": f"source_{table}_read_failed", "data": {"detail": res.get("error")}}
            data[table] = res.get("data") or []
        return {"ok": True, "data": data}

    def _map_all(self, source: dict[str, list[dict]], target_empresa_id: str) -> dict:
        warnings: list[str] = []
        viajes = source.get("viajes") or []
        gastos = source.get("gastos") or []
        pagos = source.get("pagos") or []
        cxc = source.get("cuentas_por_cobrar") or []
        docs = source.get("viaje_docs") or []

        driver_by_name = self._drivers(viajes, gastos)
        expenses_by_trip = defaultdict(float)
        for gasto in gastos:
            expenses_by_trip[str(gasto.get("numero_viaje") or "").strip()] += self._amount(gasto.get("monto_gasto"))
        for viaje in viajes:
            expenses_by_trip[str(viaje.get("folio") or "").strip()] += self._amount(viaje.get("costo_viaje"))

        rows = {
            "drivers": self._driver_rows(driver_by_name, target_empresa_id),
            "units": [],
            "trips": [],
            "expenses": [],
            "payments": [],
            "receivables": [],
            "trip_docs": [],
        }

        trip_folios = set()
        trip_aliases: dict[str, str] = {}
        for viaje in viajes:
            folio = str(viaje.get("folio") or "").strip()
            if not folio:
                warnings.append("viaje sin folio omitido")
                continue
            trip_folios.add(folio)
            for alias in self._folio_aliases(folio):
                trip_aliases[alias] = folio
            sale_price = self._amount(viaje.get("precio_venta_viaje"))
            total_cost = round(expenses_by_trip.get(folio, 0.0), 2)
            rows["trips"].append({
                "empresa_id": target_empresa_id,
                "trip_folio": folio,
                "customer": self._blank(viaje.get("cliente")),
                "origin": self._blank(viaje.get("origen")),
                "destination": self._blank(viaje.get("destino")),
                "departure_date": self._date(viaje.get("fecha_salida")),
                "arrival_date": self._date(viaje.get("fecha_llegada")),
                "trip_cost": total_cost,
                "sale_price": sale_price,
                "trip_profit": round(sale_price - total_cost, 2),
                "currency": "MXN",
                "driver_key": driver_by_name.get(str(viaje.get("chofer") or "").strip()) or None,
                "unit_key": None,
                "distance_km": None,
                "trip_status": self._trip_status(viaje.get("estatus_viaje")),
                "payment_status": self._payment_status(viaje.get("estatus_pago")),
                "doc_id": self._blank(viaje.get("id_doc")),
                "created_at": viaje.get("created_at"),
                "updated_at": viaje.get("updated_at"),
            })

            base_cost = self._amount(viaje.get("costo_viaje"))
            if base_cost > 0:
                rows["expenses"].append({
                    "empresa_id": target_empresa_id,
                    "expense_folio": f"COST-{folio}",
                    "trip_folio": folio,
                    "expense_date": self._date(viaje.get("fecha_salida")),
                    "captured_at": viaje.get("created_at"),
                    "amount": base_cost,
                    "currency": "MXN",
                    "concept": "Costo base legacy Logplat",
                    "expense_type": "base_cost",
                    "driver_key": driver_by_name.get(str(viaje.get("chofer") or "").strip()) or None,
                    "doc_id": self._blank(viaje.get("id_doc")),
                })

        for gasto in gastos:
            folio = str(gasto.get("folio") or "").strip()
            if not folio:
                warnings.append("gasto sin folio omitido")
                continue
            trip_folio = self._resolve_trip_folio(gasto.get("numero_viaje"), trip_aliases)
            if trip_folio and trip_folio not in trip_folios:
                warnings.append(f"gasto {folio} apunta a viaje inexistente {trip_folio}; queda libre")
                trip_folio = None
            rows["expenses"].append({
                "empresa_id": target_empresa_id,
                "expense_folio": folio,
                "trip_folio": trip_folio,
                "expense_date": self._date(gasto.get("fecha_gasto")),
                "captured_at": gasto.get("fecha_captura") or gasto.get("created_at"),
                "amount": self._amount(gasto.get("monto_gasto")),
                "currency": "MXN",
                "concept": self._blank(gasto.get("concepto")),
                "expense_type": self._expense_type(gasto.get("tipo_gasto"), gasto.get("concepto")),
                "driver_key": driver_by_name.get(str(gasto.get("chofer") or "").strip()) or None,
                "doc_id": self._blank(gasto.get("id_doc")),
                "created_at": gasto.get("created_at"),
                "updated_at": gasto.get("updated_at"),
            })

        for pago in pagos:
            folio = str(pago.get("folio") or "").strip()
            if not folio:
                warnings.append("pago sin folio omitido")
                continue
            trip_folio = self._resolve_trip_folio(pago.get("numero_viaje"), trip_aliases)
            if trip_folio and trip_folio not in trip_folios:
                warnings.append(f"pago {folio} apunta a viaje inexistente {trip_folio}; queda libre")
                trip_folio = None
            rows["payments"].append({
                "empresa_id": target_empresa_id,
                "payment_folio": folio,
                "trip_folio": trip_folio,
                "customer": self._blank(pago.get("cliente")),
                "payment_date": self._date(pago.get("fecha_pago")),
                "amount": self._amount(pago.get("monto_pago")),
                "currency": "MXN",
                "method": self._method(pago.get("metodo_pago")),
                "tracking_key": None,
                "notes": self._blank(pago.get("observaciones")),
                "doc_id": self._blank(pago.get("id_doc")),
                "created_at": pago.get("created_at"),
                "updated_at": pago.get("updated_at"),
            })

        for row in cxc:
            folio = str(row.get("folio") or "").strip()
            if not folio:
                warnings.append("cuenta por cobrar sin folio omitida")
                continue
            trip_folio = self._resolve_trip_folio(row.get("numero_viaje"), trip_aliases)
            rows["receivables"].append({
                "empresa_id": target_empresa_id,
                "receivable_folio": folio,
                "trip_folio": trip_folio if trip_folio in trip_folios else None,
                "customer": self._blank(row.get("cliente")),
                "total_amount": self._amount(row.get("monto_total")),
                "paid_amount": self._amount(row.get("monto_pagado")),
                "balance": self._amount(row.get("saldo_pendiente")),
                "currency": "MXN",
                "trip_date": self._date(row.get("fecha_viaje")),
                "due_date": self._date(row.get("fecha_vencimiento")),
                "collection_status": self._collection_status(row.get("estatus_cobro")),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
            })

        for doc in docs:
            folio = str(doc.get("folio") or "").strip()
            trip_folio = self._resolve_trip_folio(doc.get("viaje_folio"), trip_aliases) or ""
            if not folio or not trip_folio or trip_folio not in trip_folios:
                warnings.append(f"documento legacy omitido: {folio or 'sin_folio'}")
                continue
            rows["trip_docs"].append({
                "empresa_id": target_empresa_id,
                "doc_folio": folio,
                "trip_folio": trip_folio,
                "doc_url": doc.get("doc_url"),
                "doc_type": self._blank(doc.get("tipo")) or "other",
                "name": self._blank(doc.get("nombre")),
                "created_at": doc.get("created_at"),
            })

        return {"rows": rows, "warnings": warnings}

    def _write_target(self, target: SupabaseClient, rows: dict[str, list[dict]]) -> dict:
        order = [
            ("drivers", "empresa_id,driver_key"),
            ("units", "empresa_id,unit_key"),
            ("trips", "empresa_id,trip_folio"),
            ("expenses", "empresa_id,expense_folio"),
            ("payments", "empresa_id,payment_folio"),
            ("receivables", "empresa_id,receivable_folio"),
            ("trip_docs", "empresa_id,doc_folio"),
        ]
        written = {}
        for table, conflict in order:
            table_rows = rows.get(table) or []
            if not table_rows:
                written[table] = 0
                continue
            res = target.rest_upsert(table, table_rows, conflict)
            if not res.get("ok"):
                return {"ok": False, "error": f"target_{table}_upsert_failed", "data": {"detail": res.get("error"), "written": written}}
            written[table] = len(table_rows)
        return {"ok": True, "data": written}

    def _preview(self, source: dict[str, list[dict]], mapped: dict) -> dict:
        rows = mapped["rows"]
        return {
            "source_counts": {table: len(source.get(table) or []) for table in ("viajes", "gastos", "pagos", "cuentas_por_cobrar", "viaje_docs")},
            "target_counts": {table: len(rows.get(table) or []) for table in ("drivers", "units", "trips", "expenses", "payments", "receivables", "trip_docs")},
            "samples": {
                "trips": rows["trips"][:3],
                "expenses": rows["expenses"][:3],
                "payments": rows["payments"][:3],
                "receivables": rows["receivables"][:3],
            },
        }

    def _drivers(self, viajes: list[dict], gastos: list[dict]) -> dict[str, str]:
        names = []
        for row in viajes:
            if str(row.get("chofer") or "").strip():
                names.append(str(row.get("chofer")).strip())
        for row in gastos:
            if str(row.get("chofer") or "").strip():
                names.append(str(row.get("chofer")).strip())
        result = {}
        for name in sorted(set(names)):
            result[name] = self._key(name, "DRV")
        return result

    def _driver_rows(self, driver_by_name: dict[str, str], target_empresa_id: str) -> list[dict]:
        by_key: dict[str, str] = {}
        for name, key in sorted(driver_by_name.items(), key=lambda item: (item[1], item[0])):
            by_key.setdefault(key, name)
        return [
            {
                "empresa_id": target_empresa_id,
                "driver_key": key,
                "full_name": name,
                "pay_scheme": "per_trip",
                "pay_rate": 0,
                "status": "active",
            }
            for key, name in sorted(by_key.items())
        ]

    def _key(self, value: str, prefix: str) -> str:
        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-").upper()
        return slug[:40] or prefix

    def _folio_aliases(self, folio: str) -> set[str]:
        aliases = {folio}
        match = re.match(r"^([A-Za-z]+)-0*(\d+)$", folio.strip())
        if match:
            prefix, number = match.groups()
            n = int(number)
            aliases.add(f"{prefix.upper()}-{n}")
            aliases.add(f"{prefix.upper()}-{n:03d}")
        return aliases

    def _resolve_trip_folio(self, value: Any, aliases: dict[str, str]) -> str | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        for alias in self._folio_aliases(raw):
            if alias in aliases:
                return aliases[alias]
        return raw

    def _blank(self, value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    def _date(self, value: Any) -> str | None:
        text = str(value or "").strip()
        return text[:10] if text else None

    def _amount(self, value: Any) -> float:
        try:
            return round(float(value or 0), 2)
        except (TypeError, ValueError):
            return 0.0

    def _payment_status(self, value: Any) -> str:
        text = self._norm(value)
        if text in {"pagado", "paid"}:
            return "paid"
        if text in {"parcial", "partial"}:
            return "partial"
        return "receivable"

    def _trip_status(self, value: Any) -> str:
        text = self._norm(value)
        if text in {"cerrado", "closed"}:
            return "closed"
        if text in {"cancelado", "cancelled", "canceled"}:
            return "cancelled"
        return "active"

    def _collection_status(self, value: Any) -> str:
        text = self._norm(value)
        if text in {"pagado", "paid"}:
            return "paid"
        if text in {"parcial", "partial"}:
            return "partial"
        if text in {"vencido", "overdue"}:
            return "overdue"
        return "pending"

    def _method(self, value: Any) -> str:
        text = self._norm(value)
        if text in {"efectivo", "cash"}:
            return "cash"
        if text in {"cheque", "check"}:
            return "check"
        if text in {"tarjeta", "card"}:
            return "card"
        return "transfer"

    def _expense_type(self, value: Any, concept: Any) -> str:
        text = self._norm(value) or self._norm(concept)
        if any(item in text for item in ("diesel", "gasolina", "combustible", "fuel")):
            return "fuel"
        if any(item in text for item in ("caseta", "peaje", "toll")):
            return "tolls"
        if any(item in text for item in ("comida", "alimento", "food")):
            return "food"
        if any(item in text for item in ("reparacion", "taller", "llanta", "repair")):
            return "repair"
        return text or "other"

    def _norm(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
