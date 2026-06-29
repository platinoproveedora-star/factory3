from __future__ import annotations

from datetime import date
from typing import Any

from factory.engine import SupabaseClient


TABLE_CONFIG = {
    "sales_quotes": {
        "table": "sales_quotes",
        "key": "sales_quotes",
        "required": ["customer_name"],
        "order": "created_at.desc",
    },
    "sales_quote_items": {
        "table": "sales_quote_items",
        "key": "items",
        "required": ["sales_quote_id", "raw_description", "quantity"],
        "order": "created_at.asc",
    },
    "products": {
        "table": "products",
        "key": "products",
        "required": ["canonical_name"],
        "order": "canonical_name.asc",
    },
    "product_aliases": {
        "table": "product_aliases",
        "key": "aliases",
        "required": ["product_id", "alias_text"],
        "order": "created_at.desc",
    },
    "suppliers": {
        "table": "suppliers",
        "key": "suppliers",
        "required": ["name"],
        "order": "name.asc",
    },
    "supplier_contacts": {
        "table": "supplier_contacts",
        "key": "contacts",
        "required": ["supplier_id"],
        "order": "created_at.desc",
    },
    "supplier_categories": {
        "table": "supplier_categories",
        "key": "categories",
        "required": ["supplier_id", "category_name"],
        "order": "priority.asc,created_at.desc",
    },
    "purchase_quotes": {
        "table": "purchase_quotes",
        "key": "purchase_quotes",
        "required": ["supplier_id"],
        "order": "created_at.desc",
    },
    "purchase_quote_items": {
        "table": "purchase_quote_items",
        "key": "items",
        "required": ["purchase_quote_id", "raw_description", "quantity"],
        "order": "created_at.asc",
    },
    "purchase_quote_responses": {
        "table": "purchase_quote_responses",
        "key": "responses",
        "required": ["purchase_quote_id", "supplier_id"],
        "order": "created_at.desc",
    },
    "price_history": {
        "table": "price_history",
        "key": "price_history",
        "required": ["product_id", "supplier_id", "unit_price"],
        "order": "price_date.desc,created_at.desc",
    },
    "documents": {
        "table": "documents",
        "key": "documents",
        "required": ["file_name"],
        "order": "created_at.desc",
    },
    "activity_logs": {
        "table": "activity_logs",
        "key": "activity_logs",
        "required": ["action"],
        "order": "created_at.desc",
    },
    "settings": {
        "table": "settings",
        "key": "settings",
        "required": [],
        "order": "created_at.desc",
    },
}


WRAPPER_TABLES = {
    "sales_quote": "sales_quotes",
    "sales_quote_items": "sales_quote_items",
    "supplier_registry": "suppliers",
    "supplier_search": "suppliers",
    "supplier_category": "supplier_categories",
    "purchase_quote_generator": "purchase_quotes",
    "purchase_quote_response_ingestion": "purchase_quote_responses",
    "price_history": "price_history",
    "price_context": "price_history",
    "documents": "documents",
    "activity_log": "activity_logs",
    "settings": "settings",
}


def resolve_context(context: dict[str, Any]) -> dict[str, Any]:
    schema = str(context.get("schema") or context.get("supabase_schema") or "").strip()
    company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
    project_code = str(context.get("project_code") or "").strip()
    module_code = str(context.get("module_code") or "").strip()
    missing = [
        key
        for key, value in {
            "schema": schema,
            "company_id": company_id,
            "project_code": project_code,
            "module_code": module_code,
        }.items()
        if not value
    ]
    if missing:
        return {"ok": False, "error": f"contexto requerido: {', '.join(missing)}"}
    return {
        "ok": True,
        "data": {
            **context,
            "schema": schema,
            "supabase_schema": schema,
            "company_id": company_id,
            "empresa_id": company_id,
            "project_code": project_code,
            "module_code": module_code,
        },
    }


def clean_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value is not None}


class MultiShopperCrudService:
    def __init__(self, table_key: str):
        if table_key not in TABLE_CONFIG:
            raise ValueError(f"tabla no soportada: {table_key}")
        self.table_key = table_key
        self.config = TABLE_CONFIG[table_key]

    def ejecutar(self, context: dict[str, Any]) -> dict[str, Any]:
        action = str(context.get("action") or "list").strip()
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        if action == "list":
            return self.list(ctx)
        if action == "get":
            return self.get(ctx)
        if action == "create":
            return self.create(ctx)
        if action == "update":
            return self.update(ctx)
        if action == "delete":
            return self.delete(ctx)
        return {"ok": False, "error": f"action no soportada: {action}"}

    def list(self, context: dict[str, Any]) -> dict[str, Any]:
        filters = {"company_id": context["company_id"]}
        for key in ("status", "sales_quote_id", "purchase_quote_id", "supplier_id", "product_id"):
            if context.get(key):
                filters[key] = context[key]
        limit = int(context.get("limit") or 500)
        result = SupabaseClient(context).rest_select(
            self.config["table"],
            filters=filters,
            select="*",
            order=self.config["order"],
            limit=limit,
        )
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {self.config["key"]: result.get("data") or []}}

    def get(self, context: dict[str, Any]) -> dict[str, Any]:
        filters = self._id_filter(context)
        if not filters:
            return {"ok": False, "error": "id o folio requerido"}
        filters["company_id"] = context["company_id"]
        result = SupabaseClient(context).rest_select(self.config["table"], filters=filters, select="*", limit=1)
        if not result.get("ok"):
            return result
        rows = result.get("data") or []
        return {"ok": True, "data": {self.config["table"][:-1] if self.config["table"].endswith("s") else self.config["table"]: rows[0] if rows else None}}

    def create(self, context: dict[str, Any]) -> dict[str, Any]:
        missing = [field for field in self.config["required"] if context.get(field) in (None, "")]
        if missing:
            return {"ok": False, "error": f"campos requeridos: {', '.join(missing)}"}
        row = self._payload(context)
        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "preview": row}}
        result = SupabaseClient(context).rest_insert(self.config["table"], clean_row(row))
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        saved = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {self._singular_key(): saved}}

    def update(self, context: dict[str, Any]) -> dict[str, Any]:
        filters = self._id_filter(context)
        if not filters:
            return {"ok": False, "error": "id o folio requerido"}
        filters["company_id"] = context["company_id"]
        row = self._payload(context, include_identity=False)
        if not row:
            return {"ok": False, "error": "sin campos para actualizar"}
        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "preview": row, "filters": filters}}
        result = SupabaseClient(context).rest_update(self.config["table"], clean_row(row), filters)
        if not result.get("ok"):
            return result
        data = result.get("data") or []
        saved = data[0] if isinstance(data, list) and data else data
        return {"ok": True, "data": {self._singular_key(): saved}}

    def delete(self, context: dict[str, Any]) -> dict[str, Any]:
        filters = self._id_filter(context)
        if not filters:
            return {"ok": False, "error": "id o folio requerido"}
        filters["company_id"] = context["company_id"]
        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "filters": filters}}
        result = SupabaseClient(context).rest_delete(self.config["table"], filters)
        if not result.get("ok"):
            return result
        return {"ok": True, "data": {"deleted": True}}

    def _id_filter(self, context: dict[str, Any]) -> dict[str, Any]:
        if context.get("id"):
            return {"id": context["id"]}
        if context.get("folio"):
            return {"folio": context["folio"]}
        return {}

    def _singular_key(self) -> str:
        table = self.config["table"]
        if table == "price_history":
            return "price"
        if table.endswith("ies"):
            return table[:-3] + "y"
        if table.endswith("s"):
            return table[:-1]
        return table

    def _payload(self, context: dict[str, Any], include_identity: bool = True) -> dict[str, Any]:
        blocked = {
            "action",
            "dry_run",
            "schema",
            "supabase_schema",
            "db_schema",
            "empresa_id",
            "id",
            "folio",
            "limit",
            "table",
            "skill",
            "supabase_url",
            "supabase_service_role_key",
            "supabase_anon_key",
            "supabase_access_token",
            "supabase_project_ref",
            "can_extract",
            "bucket",
        }
        row = {key: value for key, value in context.items() if key not in blocked}
        if include_identity:
            row.setdefault("company_id", context["company_id"])
            row.setdefault("project_code", context["project_code"])
            row.setdefault("module_code", context["module_code"])
            row.setdefault("created_by", context.get("created_by") or context.get("user_id") or context.get("actor"))
        if self.table_key == "sales_quotes":
            row.setdefault("quote_date", date.today().isoformat())
            row.setdefault("status", "draft")
        if self.table_key == "products":
            row.setdefault("status", "active")
        if self.table_key == "suppliers":
            row.setdefault("status", "active")
        if self.table_key == "purchase_quotes":
            row.setdefault("channel", "manual")
            row.setdefault("status", "draft")
        if self.table_key == "documents":
            row.setdefault("processing_status", "pending")
            row.setdefault("document_type", "unknown")
        if self.table_key == "settings":
            row.setdefault("default_currency", "MXN")
        return row


class MultiShopperDashboardDataService:
    def ejecutar(self, context: dict[str, Any]) -> dict[str, Any]:
        ctx_result = resolve_context(context)
        if not ctx_result.get("ok"):
            return ctx_result
        ctx = ctx_result["data"]
        db = SupabaseClient(ctx)
        data: dict[str, Any] = {}
        for table_key, config in TABLE_CONFIG.items():
            if table_key in {"sales_quote_items", "product_aliases", "supplier_contacts", "supplier_categories", "purchase_quote_items", "purchase_quote_responses", "activity_logs", "settings"}:
                continue
            result = db.rest_select(
                config["table"],
                filters={"company_id": ctx["company_id"]},
                select="*",
                order=config["order"],
                limit=int(ctx.get("limit") or 200),
            )
            if not result.get("ok"):
                return result
            data[config["key"]] = result.get("data") or []
        return {
            "ok": True,
            "data": {
                "kpis": {
                    "active_sales_quotes": len(data.get("sales_quotes", [])),
                    "products": len(data.get("products", [])),
                    "suppliers": len(data.get("suppliers", [])),
                    "purchase_quotes": len(data.get("purchase_quotes", [])),
                    "documents": len(data.get("documents", [])),
                    "price_records": len(data.get("price_history", [])),
                },
                **data,
            },
        }


def purchase_quote_message(context: dict[str, Any]) -> str:
    supplier_name = context.get("supplier_name") or "proveedor"
    items = context.get("items") or []
    lines = []
    for item in items:
        description = item.get("raw_description") or item.get("description") or item.get("product_name") or "producto"
        quantity = item.get("quantity") or 1
        unit = item.get("unit") or "pieza"
        lines.append(f"- {description}: {quantity} {unit}")
    body = "\n".join(lines) if lines else "- Productos por confirmar"
    return (
        f"Hola {supplier_name}, buen dia.\n\n"
        "Me apoyas cotizando disponibilidad, precio unitario, tiempo de entrega y vigencia para:\n\n"
        f"{body}\n\n"
        "Gracias."
    )


def schema_sql(schema: str) -> str:
    schema = str(schema or "").strip()
    if not schema:
        raise ValueError("schema requerido")
    return f"""
CREATE SCHEMA IF NOT EXISTS {schema};
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION {schema}.set_folio(prefix text, seq_name text)
RETURNS text AS $$
DECLARE
  n bigint;
BEGIN
  EXECUTE format('CREATE SEQUENCE IF NOT EXISTS {schema}.%I START 1', seq_name);
  EXECUTE format('SELECT nextval(''{schema}.%I'')', seq_name) INTO n;
  RETURN prefix || '-' || lpad(n::text, 5, '0');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION {schema}.touch_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS {schema}.sales_quotes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('MSQ', 'sales_quotes_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  created_by text,
  customer_name text NOT NULL,
  project_name text,
  quote_date date NOT NULL DEFAULT current_date,
  status text NOT NULL DEFAULT 'draft',
  notes text,
  erp_customer_id uuid,
  erp_sales_order_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.products (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('MSP', 'products_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  canonical_name text NOT NULL,
  category_id uuid,
  category_name text,
  unit text,
  brand text,
  measure text,
  description text,
  status text NOT NULL DEFAULT 'active',
  erp_product_id uuid,
  erp_inventory_item_id uuid,
  erp_unit_id uuid,
  erp_category_id uuid,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('DOC', 'documents_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  uploaded_by text,
  created_by text,
  file_name text NOT NULL,
  file_url text,
  storage_bucket text,
  storage_path text,
  file_type text,
  document_type text NOT NULL DEFAULT 'unknown',
  source_context jsonb NOT NULL DEFAULT '{{}}',
  related_sales_quote_id uuid,
  related_purchase_quote_id uuid,
  related_supplier_id uuid,
  processing_status text NOT NULL DEFAULT 'pending',
  extracted_text text,
  ai_summary text,
  extracted_data jsonb NOT NULL DEFAULT '{{}}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.sales_quote_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('SQI', 'sales_quote_items_folio_seq'),
  sales_quote_id uuid NOT NULL REFERENCES {schema}.sales_quotes(id),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  product_id uuid REFERENCES {schema}.products(id),
  raw_description text NOT NULL,
  quantity numeric NOT NULL DEFAULT 1,
  unit text,
  category_id uuid,
  category_name text,
  notes text,
  source_type text NOT NULL DEFAULT 'manual',
  source_document_id uuid REFERENCES {schema}.documents(id),
  erp_product_id uuid,
  erp_inventory_item_id uuid,
  erp_unit_id uuid,
  erp_category_id uuid,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.product_aliases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('PAL', 'product_aliases_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  product_id uuid NOT NULL REFERENCES {schema}.products(id),
  alias_text text NOT NULL,
  source_document_id uuid REFERENCES {schema}.documents(id),
  confidence_score numeric,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.suppliers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('SUP', 'suppliers_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  name text NOT NULL,
  legal_name text,
  supplier_type text,
  city text,
  state text,
  notes text,
  status text NOT NULL DEFAULT 'active',
  erp_supplier_id uuid,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.supplier_contacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('SPC', 'supplier_contacts_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  supplier_id uuid NOT NULL REFERENCES {schema}.suppliers(id),
  contact_name text,
  role text,
  email text,
  phone text,
  whatsapp text,
  preferred_channel text,
  notes text,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.supplier_categories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('CAT', 'supplier_categories_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  supplier_id uuid NOT NULL REFERENCES {schema}.suppliers(id),
  category_name text NOT NULL,
  erp_category_id uuid,
  priority integer NOT NULL DEFAULT 100,
  notes text,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.purchase_quotes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('MPQ', 'purchase_quotes_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  sales_quote_id uuid REFERENCES {schema}.sales_quotes(id),
  supplier_id uuid NOT NULL REFERENCES {schema}.suppliers(id),
  channel text NOT NULL DEFAULT 'manual',
  status text NOT NULL DEFAULT 'draft',
  subject text,
  message_body text,
  sent_manually_at timestamptz,
  erp_purchase_order_id uuid,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.purchase_quote_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('PQI', 'purchase_quote_items_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  purchase_quote_id uuid NOT NULL REFERENCES {schema}.purchase_quotes(id),
  sales_quote_item_id uuid REFERENCES {schema}.sales_quote_items(id),
  product_id uuid REFERENCES {schema}.products(id),
  raw_description text NOT NULL,
  quantity numeric NOT NULL DEFAULT 1,
  unit text,
  notes text,
  erp_product_id uuid,
  erp_inventory_item_id uuid,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.purchase_quote_responses (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('PQR', 'purchase_quote_responses_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  purchase_quote_id uuid NOT NULL REFERENCES {schema}.purchase_quotes(id),
  supplier_id uuid NOT NULL REFERENCES {schema}.suppliers(id),
  response_document_id uuid REFERENCES {schema}.documents(id),
  response_date date,
  valid_until date,
  notes text,
  status text NOT NULL DEFAULT 'response_received',
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.price_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('PRC', 'price_history_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  product_id uuid NOT NULL REFERENCES {schema}.products(id),
  supplier_id uuid NOT NULL REFERENCES {schema}.suppliers(id),
  purchase_quote_response_id uuid REFERENCES {schema}.purchase_quote_responses(id),
  source_document_id uuid REFERENCES {schema}.documents(id),
  product_name text,
  supplier_name text,
  raw_description text,
  unit text,
  quantity numeric,
  unit_price numeric NOT NULL,
  subtotal numeric,
  currency text NOT NULL DEFAULT 'MXN',
  price_type text NOT NULL DEFAULT 'supplier_cost',
  price_date date NOT NULL DEFAULT current_date,
  valid_until date,
  delivery_time text,
  payment_terms text,
  erp_product_id uuid,
  erp_supplier_id uuid,
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.activity_logs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('ACT', 'activity_logs_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  action text NOT NULL,
  entity_type text,
  entity_id uuid,
  actor text,
  detail jsonb NOT NULL DEFAULT '{{}}',
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio text UNIQUE NOT NULL DEFAULT {schema}.set_folio('SET', 'settings_folio_seq'),
  company_id text NOT NULL,
  project_code text NOT NULL,
  module_code text NOT NULL,
  default_currency text NOT NULL DEFAULT 'MXN',
  default_quote_message_template text,
  default_whatsapp_template text,
  default_email_template text,
  ocr_settings jsonb NOT NULL DEFAULT '{{}}',
  ai_normalization_settings jsonb NOT NULL DEFAULT '{{}}',
  created_by text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ms_sales_quotes_company ON {schema}.sales_quotes(company_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ms_products_company ON {schema}.products(company_id, canonical_name);
CREATE INDEX IF NOT EXISTS idx_ms_suppliers_company ON {schema}.suppliers(company_id, name);
CREATE INDEX IF NOT EXISTS idx_ms_supplier_categories_company ON {schema}.supplier_categories(company_id, category_name);
CREATE INDEX IF NOT EXISTS idx_ms_purchase_quotes_company ON {schema}.purchase_quotes(company_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ms_documents_company ON {schema}.documents(company_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ms_price_history_company ON {schema}.price_history(company_id, product_id, price_date DESC);

DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'sales_quotes','sales_quote_items','products','suppliers','supplier_contacts',
    'purchase_quotes','purchase_quote_items','purchase_quote_responses','documents','settings'
  ]
  LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%I_touch_updated_at ON {schema}.%I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%I_touch_updated_at BEFORE UPDATE ON {schema}.%I FOR EACH ROW EXECUTE FUNCTION {schema}.touch_updated_at()', t, t);
  END LOOP;
END $$;
"""
