"""Crea el schema coti4all multi-tenant en Supabase (Management API)."""
from __future__ import annotations
import json
import os
import urllib.request


_DDL = """
CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.catalog_items (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text UNIQUE NOT NULL,
  empresa_id   text NOT NULL,
  project_code text,
  module_code  text,
  sku          text,
  nombre       text NOT NULL,
  unidad       text DEFAULT 'pza',
  categoria    text,
  activo       boolean DEFAULT true,
  costo_referencia numeric(12,3) DEFAULT 0,
  attributes   jsonb DEFAULT '{}',
  tags         jsonb DEFAULT '{}',
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.price_lists (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text UNIQUE NOT NULL,
  empresa_id   text NOT NULL,
  project_code text,
  module_code  text,
  nombre       text NOT NULL,
  prioridad    int DEFAULT 0,
  moneda       text DEFAULT 'MXN',
  activo       boolean DEFAULT true,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.price_list_items (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text UNIQUE NOT NULL,
  price_list_id uuid NOT NULL REFERENCES {schema}.price_lists(id) ON DELETE CASCADE,
  empresa_id   text NOT NULL,
  sku          text NOT NULL,
  precio       numeric(12,3) DEFAULT 0,
  moneda       text,
  activo       boolean DEFAULT true,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS {schema}.quotes (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text NOT NULL,
  empresa_id   text NOT NULL,
  project_code text,
  module_code  text,
  client_party_id uuid,
  client_nombre text,
  client_email text,
  client_telefono text,
  status       text DEFAULT 'draft',
  moneda       text DEFAULT 'MXN',
  subtotal     numeric(12,2) DEFAULT 0,
  impuesto     numeric(12,2) DEFAULT 0,
  total        numeric(12,2) DEFAULT 0,
  costo_total  numeric(12,2) DEFAULT 0,
  margen       numeric(12,2) DEFAULT 0,
  margen_pct   numeric(6,3) DEFAULT 0,
  validez_dias int DEFAULT 15,
  notas        text,
  metadata     jsonb DEFAULT '{}',
  pdf_url      text,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now(),
  UNIQUE (empresa_id, folio)
);

CREATE TABLE IF NOT EXISTS {schema}.quote_items (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text NOT NULL,
  quote_id     uuid NOT NULL REFERENCES {schema}.quotes(id) ON DELETE CASCADE,
  empresa_id   text NOT NULL,
  sku          text,
  nombre       text NOT NULL,
  cantidad     numeric(12,3) DEFAULT 0,
  unidad       text DEFAULT 'pza',
  precio_unitario numeric(12,2) DEFAULT 0,
  costo_unitario  numeric(12,2) DEFAULT 0,
  line_subtotal   numeric(12,2) DEFAULT 0,
  line_costo      numeric(12,2) DEFAULT 0,
  line_margen     numeric(12,2) DEFAULT 0,
  line_margen_pct numeric(6,3) DEFAULT 0,
  impuesto_pct    numeric(6,3) DEFAULT 0,
  line_impuesto   numeric(12,2) DEFAULT 0,
  line_total      numeric(12,2) DEFAULT 0,
  peso_kg      numeric(12,3),
  notas        text,
  attributes   jsonb DEFAULT '{}',
  orden        int,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now(),
  UNIQUE (empresa_id, folio)
);

CREATE TABLE IF NOT EXISTS {schema}.quote_events (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text NOT NULL,
  quote_id     uuid NOT NULL REFERENCES {schema}.quotes(id) ON DELETE CASCADE,
  evento       text NOT NULL,
  detalle      jsonb DEFAULT '{}',
  usuario      text,
  empresa_id   text NOT NULL,
  created_at   timestamptz DEFAULT now(),
  UNIQUE (empresa_id, folio)
);

CREATE INDEX IF NOT EXISTS idx_cot4_catalog_empresa ON {schema}.catalog_items(empresa_id, sku);
CREATE INDEX IF NOT EXISTS idx_cot4_price_list_empresa ON {schema}.price_lists(empresa_id);
CREATE INDEX IF NOT EXISTS idx_cot4_price_items_pl ON {schema}.price_list_items(price_list_id, sku);
CREATE INDEX IF NOT EXISTS idx_cot4_quotes_empresa ON {schema}.quotes(empresa_id, status);
CREATE INDEX IF NOT EXISTS idx_cot4_quote_items_quote ON {schema}.quote_items(quote_id, sku);
CREATE INDEX IF NOT EXISTS idx_cot4_quote_events_quote ON {schema}.quote_events(quote_id);

GRANT USAGE ON SCHEMA {schema} TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA {schema}
  GRANT ALL ON TABLES TO anon, authenticated, service_role;
"""


class Coti4AllSchemaSetupService:
    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", True)
        schema = self._resolve_schema(context)
        if not schema:
            return {"ok": False, "error": "schema requerido en context o env COTI4ALL_SCHEMA"}
        sql = _DDL.strip().replace("{schema}", schema)

        if dry_run:
            return {"ok": True, "message": "dry_run — SQL no ejecutado", "data": {"schema": schema, "sql": sql}}

        project_ref = self._project_ref()
        if not project_ref:
            return {"ok": False, "error": "No se pudo obtener SUPABASE_PROJECT_REF o SUPABASE_URL"}
        token = os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()
        if not token:
            return {"ok": False, "error": "SUPABASE_ACCESS_TOKEN requerido"}

        try:
            self._run_sql(project_ref, token, sql)
            return {
                "ok": True,
                "message": f"Schema {schema} creado correctamente",
                "data": {
                    "schema": schema,
                    "tables": [
                        "catalog_items",
                        "price_lists",
                        "price_list_items",
                        "quotes",
                        "quote_items",
                        "quote_events",
                    ],
                    "note": "Exponer el schema en Supabase Dashboard → Settings → API → Exposed schemas",
                },
            }
        except Exception as exc:
            return {"ok": False, "error": f"Error ejecutando DDL: {exc}"}

    def _resolve_schema(self, context: dict) -> str | None:
        return str(context.get("schema") or context.get("supabase_schema") or os.getenv("COTI4ALL_SCHEMA", "") or "").strip() or None

    def _project_ref(self) -> str:
        ref = os.getenv("SUPABASE_PROJECT_REF", "").strip()
        if ref:
            return ref
        url = os.getenv("SUPABASE_URL", "").strip()
        if url:
            return url.replace("https://", "").replace("http://", "").split(".")[0]
        return ""

    def _run_sql(self, project_ref: str, token: str, sql: str) -> None:
        payload = json.dumps({"query": sql}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.supabase.com/v1/projects/{project_ref}/database/query",
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
