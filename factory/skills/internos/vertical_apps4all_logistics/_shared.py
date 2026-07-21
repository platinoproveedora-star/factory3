from __future__ import annotations

import importlib.util
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from factory.engine import SupabaseClient


_SKILLS_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_TRIP_STATUS = {"borrador", "programado", "confirmado", "en_ruta"}
LOCKED_TRIP_STATUS = {"confirmado", "en_ruta", "completado", "cancelado"}
VALID_TRIP_STATUS = {"borrador", "programado", "confirmado", "en_ruta", "completado", "cancelado"}


def resolve_context(context: dict) -> dict:
    service_path = _SKILLS_ROOT / "vertical_erp" / "erp_project_context_resolve" / "service.py"
    spec = importlib.util.spec_from_file_location("erp_project_context_resolve_service", service_path)
    if spec is None or spec.loader is None:
        return {"ok": False, "error": "no se pudo cargar erp_project_context_resolve"}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.ErpProjectContextResolveService().ejecutar(
        {
            **context,
            "module_code": context.get("module_code") or "logistics",
            "schema": context.get("schema") or context.get("logistics_schema") or context.get("supabase_schema"),
        }
    )
    if not result.get("ok"):
        return result
    data = result.get("data") or {}
    company_id = str(data.get("company_id") or data.get("empresa_id") or "").strip()
    sales_schema = str(context.get("sales_schema") or context.get("schema_ventas") or data.get("sales_schema") or "").strip()
    if not sales_schema:
        return {"ok": False, "error": "sales_schema/schema_ventas requerido"}
    access = validate_access(context, company_id)
    if not access.get("ok"):
        return access
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    trip_defaults = project.get("trip_defaults") if isinstance(project.get("trip_defaults"), dict) else {}
    return {
        "ok": True,
        "data": {
            **data,
            "company_id": company_id,
            "empresa_id": company_id,
            "schema": data.get("schema"),
            "sales_schema": sales_schema,
            "project_code": data.get("project_code"),
            "module_code": data.get("module_code") or "logistics",
            "duration_minutes_default": int(trip_defaults.get("duration_minutes") or 120),
            "key_products": project.get("key_products") if isinstance(project.get("key_products"), list) else [],
        },
    }


def validate_access(context: dict, company_id: str) -> dict:
    role = str(context.get("role") or context.get("user_role") or "").strip()
    if role in {"platform_admin", "admin_global"}:
        return {"ok": True}
    allowed = context.get("allowed_company_ids")
    if isinstance(allowed, str):
        allowed = [item.strip() for item in allowed.split(",") if item.strip()]
    if isinstance(allowed, list) and allowed and company_id not in {str(item) for item in allowed}:
        return {"ok": False, "error": "usuario sin acceso a esta empresa"}
    return {"ok": True}


def db(ctx: dict) -> SupabaseClient:
    return SupabaseClient({**ctx, "schema": ctx["schema"]})


def sales_db(ctx: dict) -> SupabaseClient:
    return SupabaseClient({**ctx, "schema": ctx["sales_schema"]})


def is_dry_run(context: dict) -> bool:
    return bool(context.get("dry_run", True))


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def table_filters(ctx: dict, extra: dict | None = None) -> dict:
    filters = {
        "empresa_id": f"eq.{ctx['company_id']}",
        "project_code": f"eq.{ctx['project_code']}",
        "module_code": f"eq.{ctx['module_code']}",
    }
    filters.update(extra or {})
    return filters


def reserve_folio(ctx: dict, table: str, prefix: str) -> dict:
    result = db(ctx).rest_select(table, filters={"folio": f"ilike.{prefix}-%"}, select="folio", limit=10000)
    if not result.get("ok"):
        return result
    max_num = 0
    for row in result.get("data") or []:
        match = re.match(rf"^{re.escape(prefix)}-(\d+)$", str(row.get("folio") or ""))
        if match:
            max_num = max(max_num, int(match.group(1)))
    return {"ok": True, "data": {"folio": f"{prefix}-{max_num + 1:05d}"}}


def create_sql(schema: str) -> str:
    return f"""
create schema if not exists {schema};

create table if not exists {schema}.logistics_trips (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  fecha_viaje date,
  hora_inicio time,
  duracion_minutos integer not null default 120 check (duracion_minutos > 0),
  vehiculo_id uuid,
  driver_id uuid,
  estado text not null default 'borrador' check (estado in ('borrador','programado','confirmado','en_ruta','completado','cancelado')),
  notes text,
  erp_tags jsonb not null default '{{}}',
  metadata jsonb not null default '{{}}',
  created_by_user_id uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {schema}.logistics_trip_orders (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  trip_id uuid not null references {schema}.logistics_trips(id) on delete cascade,
  pedido_id uuid not null,
  pedido_folio text,
  peso_override_kg numeric(14,4),
  fecha_entrega_override date,
  orden_carga integer,
  notes text,
  erp_tags jsonb not null default '{{}}',
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique (trip_id, pedido_id)
);

alter table {schema}.logistics_trip_orders
  add column if not exists fecha_entrega_override date;

create table if not exists {schema}.logistics_vehicles (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  nombre text not null,
  tipo text,
  placa text,
  capacidad_peso_kg numeric(14,4),
  status text not null default 'disponible' check (status in ('disponible','en_ruta','mantenimiento','inactivo')),
  activo boolean not null default true,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {schema}.logistics_drivers (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  nombre text not null,
  telefono text,
  status text not null default 'activo' check (status in ('activo','inactivo')),
  activo boolean not null default true,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create table if not exists {schema}.logistics_product_config (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null,
  product_key text not null,
  product_label text not null,
  priority integer not null default 100,
  active boolean not null default true,
  metadata jsonb not null default '{{}}',
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  unique (empresa_id, project_code, module_code, product_key)
);

create index if not exists idx_logistics_trips_company_status on {schema}.logistics_trips (empresa_id, estado, fecha_viaje);
create index if not exists idx_logistics_trip_orders_trip on {schema}.logistics_trip_orders (trip_id);
create index if not exists idx_logistics_trip_orders_pedido on {schema}.logistics_trip_orders (empresa_id, pedido_id);

grant usage on schema {schema} to anon, authenticated, service_role;
grant select, insert, update, delete on all tables in schema {schema} to service_role;
grant select on all tables in schema {schema} to authenticated;
alter default privileges in schema {schema} grant select, insert, update, delete on tables to service_role;
alter default privileges in schema {schema} grant select on tables to authenticated;

notify pgrst, 'reload schema';
""".strip()


def list_trips(ctx: dict, include_cancelled: bool = False) -> list[dict]:
    filters = table_filters(ctx)
    if not include_cancelled:
        filters["estado"] = "neq.cancelado"
    result = db(ctx).rest_select("logistics_trips", filters=filters, select="*", order="fecha_viaje.asc,hora_inicio.asc,created_at.desc", limit=1000)
    return result.get("data") if result.get("ok") and isinstance(result.get("data"), list) else []


def list_trip_orders(ctx: dict) -> list[dict]:
    result = db(ctx).rest_select("logistics_trip_orders", filters=table_filters(ctx), select="*", order="orden_carga.asc,created_at.asc", limit=5000)
    return result.get("data") if result.get("ok") and isinstance(result.get("data"), list) else []


def list_catalogs(ctx: dict) -> dict:
    vehicles = db(ctx).rest_select("logistics_vehicles", filters=table_filters(ctx, {"activo": "eq.true"}), select="*", order="nombre.asc", limit=500)
    drivers = db(ctx).rest_select("logistics_drivers", filters=table_filters(ctx, {"activo": "eq.true"}), select="*", order="nombre.asc", limit=500)
    products = db(ctx).rest_select("logistics_product_config", filters=table_filters(ctx, {"active": "eq.true"}), select="*", order="priority.asc,product_label.asc", limit=500)
    return {
        "vehicles": vehicles.get("data") if vehicles.get("ok") else [],
        "drivers": drivers.get("data") if drivers.get("ok") else [],
        "product_config": products.get("data") if products.get("ok") else [],
    }


def list_orders(ctx: dict, limit: int = 500) -> list[dict]:
    docs = sales_db(ctx).rest_select(
        "sales_documents",
        filters={"empresa_id": f"eq.{ctx['company_id']}", "document_type": "eq.pedido", "status": "in.(pedido,liberado)"},
        select="id,folio,external_folio,customer_id,customer_name_snapshot,status,document_date,due_date,delivery_address,payment_method,city,city_quadrant,total_weight_kg,subtotal,tax_total,total,balance_total,notes,metadata,created_at",
        order="due_date.asc,created_at.desc",
        limit=limit,
    )
    if not docs.get("ok"):
        return []
    rows = docs.get("data") or []
    if not rows:
        return []
    ids = [str(row["id"]) for row in rows if row.get("id")]
    items = sales_db(ctx).rest_select(
        "sales_document_items",
        filters={"document_id": f"in.({','.join(ids)})"},
        select="id,folio,document_id,product_id,inventory_product_id,product_folio_snapshot,product_name_snapshot,description,quantity,unit,line_total,weight_kg_total,weight_source,created_at",
        order="created_at.asc",
        limit=5000,
    )
    by_doc: dict[str, list[dict]] = {}
    if items.get("ok"):
        for item in items.get("data") or []:
            by_doc.setdefault(str(item.get("document_id") or ""), []).append(item)
    return [format_order(row, by_doc.get(str(row.get("id") or ""), [])) for row in rows]


def format_order(row: dict, items: list[dict]) -> dict:
    parts = []
    for item in items:
        name = str(item.get("product_name_snapshot") or item.get("description") or "").strip()
        qty = item.get("quantity") or 0
        unit = str(item.get("unit") or "").strip()
        label = f"{name} {num(qty)} {unit}".strip()
        parts.append(label)
    return {
        **row,
        "fecha_entrega": row.get("due_date") or row.get("document_date"),
        "peso_kg": float(row.get("total_weight_kg") or 0),
        "importe": float(row.get("total") or 0),
        "partida_1": parts[0] if len(parts) > 0 else "",
        "partida_2": parts[1] if len(parts) > 1 else "",
        "partida_3": parts[2] if len(parts) > 2 else "",
        "otras_partidas": f"+{len(parts) - 3} partidas" if len(parts) > 3 else "",
        "items": items,
    }


def num(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return "0"
    return str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0").rstrip(".")


def attach_orders_to_trips(trips: list[dict], orders: list[dict], trip_orders: list[dict]) -> list[dict]:
    orders_by_id = {str(order.get("id")): order for order in orders}
    by_trip: dict[str, list[dict]] = {}
    for link in trip_orders:
        order = orders_by_id.get(str(link.get("pedido_id")))
        if order:
            override = link.get("peso_override_kg")
            fecha_entrega = link.get("fecha_entrega_override") or order.get("fecha_entrega")
            by_trip.setdefault(str(link.get("trip_id")), []).append(
                {
                    **order,
                    "trip_order": link,
                    "fecha_entrega": fecha_entrega,
                    "peso_kg": float(override if override is not None else order.get("peso_kg") or 0),
                }
            )
    enriched = []
    for trip in trips:
        rows = by_trip.get(str(trip.get("id")), [])
        enriched.append({**trip, "hora_fin": trip_end_time(trip), "orders": rows, "summary": summarize_trip(rows)})
    return enriched


def summarize_trip(orders: list[dict]) -> dict:
    product_totals: dict[str, dict] = {}
    peso_total = 0.0
    importe_total = 0.0
    for order in orders:
        peso_total += float(order.get("peso_kg") or 0)
        importe_total += float(order.get("importe") or order.get("total") or 0)
        for item in order.get("items") or []:
            product_id = str(item.get("inventory_product_id") or item.get("product_id") or item.get("description") or "")
            name = str(item.get("product_name_snapshot") or item.get("description") or "Producto").strip()
            current = product_totals.setdefault(product_id, {"product_id": product_id, "product_name": name, "quantity": 0.0, "unit": item.get("unit"), "line_total": 0.0, "weight_kg_total": 0.0})
            current["quantity"] += float(item.get("quantity") or 0)
            current["line_total"] += float(item.get("line_total") or 0)
            current["weight_kg_total"] += float(item.get("weight_kg_total") or 0)
    products = sorted(product_totals.values(), key=lambda row: (row["quantity"], row["line_total"]), reverse=True)
    return {"orders_count": len(orders), "peso_total_kg": round(peso_total, 4), "importe_total": round(importe_total, 2), "product_totals": products, "key_products": products[:4]}


def trip_end_time(trip: dict) -> str | None:
    if not trip.get("hora_inicio"):
        return None
    try:
        start = datetime.strptime(str(trip["hora_inicio"])[:5], "%H:%M")
        end = start + timedelta(minutes=int(trip.get("duracion_minutos") or 120))
        return end.strftime("%H:%M")
    except Exception:
        return None


def computed_status(values: dict, current: str = "borrador") -> str:
    if current not in {"borrador", "programado"}:
        return current
    required = [values.get("fecha_viaje"), values.get("hora_inicio"), values.get("duracion_minutos"), values.get("vehiculo_id"), values.get("driver_id")]
    return "programado" if all(required) else "borrador"


def active_assigned_pedido_ids(trips: list[dict], trip_orders: list[dict]) -> set[str]:
    active_trip_ids = {str(trip.get("id")) for trip in trips if str(trip.get("estado") or "") in ACTIVE_TRIP_STATUS}
    return {str(link.get("pedido_id")) for link in trip_orders if str(link.get("trip_id")) in active_trip_ids}
