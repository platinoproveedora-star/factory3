"""Crea el schema factu4all multi-tenant en Supabase (Management API)."""
from __future__ import annotations
import json
import os
import urllib.request


_DDL = """
CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.factu4all_company_settings (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio                text UNIQUE NOT NULL,
  company_id           text NOT NULL,
  country              text DEFAULT 'MX',
  default_pac_provider text,
  default_environment  text DEFAULT 'sandbox',
  created_at           timestamptz DEFAULT now(),
  updated_at           timestamptz DEFAULT now(),
  metadata             jsonb DEFAULT '{}',
  UNIQUE (company_id)
);

CREATE TABLE IF NOT EXISTS {schema}.pac_accounts (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio          text UNIQUE NOT NULL,
  company_id     text NOT NULL,
  pac_provider   text NOT NULL,
  environment    text DEFAULT 'sandbox',
  credential_ref text,
  status         text DEFAULT 'draft',
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now(),
  metadata       jsonb DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS {schema}.issuer_profiles (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio             text UNIQUE NOT NULL,
  company_id        text NOT NULL,
  rfc               text NOT NULL,
  legal_name        text NOT NULL,
  fiscal_regime     text,
  expedition_place  text,
  commercial_name   text,
  fiscal_email      text,
  fiscal_address    text,
  pac_provider      text,
  pac_account_id    uuid REFERENCES {schema}.pac_accounts(id),
  csd_status        text DEFAULT 'pending',
  environment       text DEFAULT 'sandbox',
  status            text DEFAULT 'draft',
  created_at        timestamptz DEFAULT now(),
  updated_at        timestamptz DEFAULT now(),
  metadata          jsonb DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS {schema}.folio_series (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio          text UNIQUE NOT NULL,
  company_id     text NOT NULL,
  cfdi_type      text NOT NULL,
  series         text NOT NULL,
  current_number int DEFAULT 0,
  next_number    int DEFAULT 1,
  environment    text DEFAULT 'sandbox',
  pac_provider   text,
  is_default     boolean DEFAULT false,
  status         text DEFAULT 'active',
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now(),
  metadata       jsonb DEFAULT '{}',
  UNIQUE (company_id, series, cfdi_type, environment)
);

CREATE TABLE IF NOT EXISTS {schema}.parties (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio              text UNIQUE NOT NULL,
  company_id         text NOT NULL,
  source_system      text,
  source_schema      text,
  source_table       text,
  source_id          text,
  source_folio       text,
  party_type         text NOT NULL,
  source_display_name text,
  rfc                text,
  legal_name         text,
  tax_regime         text,
  tax_zip_code       text,
  cfdi_use_default   text,
  billing_email      text,
  billing_address    text,
  status             text DEFAULT 'active',
  created_at         timestamptz DEFAULT now(),
  updated_at         timestamptz DEFAULT now(),
  metadata           jsonb DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS {schema}.products (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio               text UNIQUE NOT NULL,
  company_id          text NOT NULL,
  source_system       text,
  source_schema       text,
  source_table        text,
  source_id           text,
  source_folio        text,
  source_product_key  text,
  source_product_name text,
  fiscal_product_name text,
  fiscal_description  text,
  sat_product_key     text,
  sat_unit_key        text,
  sat_unit_name       text,
  tax_object          text,
  iva_rate            numeric(6,4) DEFAULT 0.16,
  ieps_rate           numeric(6,4) DEFAULT 0,
  category            text,
  sat_group_key       text,
  status              text DEFAULT 'revisar',
  created_at          timestamptz DEFAULT now(),
  updated_at          timestamptz DEFAULT now(),
  metadata            jsonb DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS {schema}.cfdi_documents (
  id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio                     text UNIQUE NOT NULL,
  company_id                text NOT NULL,
  direction                 text NOT NULL DEFAULT 'issued',
  cfdi_type                 text,
  business_effect           text,
  source_system             text,
  source_schema             text,
  source_table              text,
  source_type               text,
  source_id                 text,
  source_folio              text,
  issuer_profile_id         uuid REFERENCES {schema}.issuer_profiles(id),
  issuer_rfc_snapshot       text,
  issuer_legal_name_snapshot text,
  party_id                  uuid REFERENCES {schema}.parties(id),
  party_type                text,
  party_rfc_snapshot        text,
  party_legal_name_snapshot text,
  payment_method            text,
  payment_form              text,
  currency                  text DEFAULT 'MXN',
  pac_provider              text,
  pac_account_id            uuid REFERENCES {schema}.pac_accounts(id),
  environment               text DEFAULT 'sandbox',
  series                    text,
  cfdi_folio                text,
  uuid                      text,
  status                    text DEFAULT 'draft',
  subtotal                  numeric(14,2) DEFAULT 0,
  discount_total            numeric(14,2) DEFAULT 0,
  tax_total                 numeric(14,2) DEFAULT 0,
  total                     numeric(14,2) DEFAULT 0,
  xml_storage_path          text,
  pdf_storage_path          text,
  pac_request               jsonb,
  pac_response              jsonb,
  pac_error                 text,
  issued_at                 timestamptz,
  cancelled_at              timestamptz,
  created_at                timestamptz DEFAULT now(),
  updated_at                timestamptz DEFAULT now(),
  metadata                  jsonb DEFAULT '{}'
);

ALTER TABLE {schema}.cfdi_item_movements ADD COLUMN IF NOT EXISTS tax_object_snapshot text;
ALTER TABLE {schema}.cfdi_documents ADD COLUMN IF NOT EXISTS issuer_profile_id uuid REFERENCES {schema}.issuer_profiles(id);
ALTER TABLE {schema}.cfdi_documents ADD COLUMN IF NOT EXISTS issuer_rfc_snapshot text;
ALTER TABLE {schema}.cfdi_documents ADD COLUMN IF NOT EXISTS issuer_legal_name_snapshot text;

DROP INDEX IF EXISTS {schema}.uq_factu4all_no_double_stamp;
CREATE UNIQUE INDEX IF NOT EXISTS uq_factu4all_no_double_stamp
  ON {schema}.cfdi_documents (company_id, source_system, source_type, source_id)
  WHERE status IN ('stamped', 'simulated');

CREATE TABLE IF NOT EXISTS {schema}.cfdi_item_movements (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio                       text UNIQUE NOT NULL,
  company_id                  text NOT NULL,
  cfdi_document_id            uuid REFERENCES {schema}.cfdi_documents(id) ON DELETE CASCADE,
  uuid                        text,
  movement_direction          text NOT NULL,
  document_direction          text,
  business_effect             text,
  source_document_id          text,
  source_document_folio       text,
  party_id                    uuid REFERENCES {schema}.parties(id),
  party_type                  text,
  product_id                  uuid REFERENCES {schema}.products(id),
  source_product_id           text,
  source_product_key          text,
  source_product_name         text,
  fiscal_product_name_snapshot text,
  sat_product_key_snapshot    text,
  sat_unit_key_snapshot       text,
  sat_group_key_snapshot      text,
  tax_object_snapshot         text,
  quantity                    numeric(14,4) DEFAULT 0,
  unit_price                  numeric(14,4) DEFAULT 0,
  subtotal                    numeric(14,2) DEFAULT 0,
  discount_amount              numeric(14,2) DEFAULT 0,
  tax_amount                  numeric(14,2) DEFAULT 0,
  total                       numeric(14,2) DEFAULT 0,
  issued_at                   timestamptz,
  cancelled_at                timestamptz,
  created_at                  timestamptz DEFAULT now(),
  metadata                    jsonb DEFAULT '{}'
);

ALTER TABLE {schema}.cfdi_item_movements ADD COLUMN IF NOT EXISTS environment text;
ALTER TABLE {schema}.cfdi_item_movements ADD COLUMN IF NOT EXISTS balance_after numeric(14,4);

CREATE TABLE IF NOT EXISTS {schema}.product_stock (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id     text NOT NULL,
  product_id     uuid NOT NULL REFERENCES {schema}.products(id) ON DELETE CASCADE,
  environment    text NOT NULL DEFAULT 'sandbox',
  current_stock  numeric(14,4) NOT NULL DEFAULT 0,
  updated_at     timestamptz DEFAULT now(),
  UNIQUE (company_id, product_id, environment)
);

CREATE TABLE IF NOT EXISTS {schema}.document_files (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio             text UNIQUE NOT NULL,
  company_id        text NOT NULL,
  cfdi_document_id  uuid REFERENCES {schema}.cfdi_documents(id) ON DELETE CASCADE,
  uuid              text,
  file_type         text NOT NULL,
  storage_bucket    text DEFAULT 'factu4all-documents',
  storage_path      text,
  content_type      text,
  size_bytes        bigint,
  checksum          text,
  created_at        timestamptz DEFAULT now(),
  metadata          jsonb DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS {schema}.source_catalogs (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio          text UNIQUE NOT NULL,
  company_id     text NOT NULL,
  source_system  text NOT NULL,
  source_schema  text NOT NULL,
  source_table   text NOT NULL,
  catalog_type   text NOT NULL,
  label          text,
  status         text DEFAULT 'active',
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now(),
  metadata       jsonb DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS {schema}.product_source_links (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio          text UNIQUE NOT NULL,
  company_id     text NOT NULL,
  product_id     uuid REFERENCES {schema}.products(id) ON DELETE CASCADE,
  source_system  text NOT NULL,
  source_schema  text NOT NULL,
  source_table   text NOT NULL,
  source_id      text NOT NULL,
  source_key     text,
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now(),
  metadata       jsonb DEFAULT '{}',
  UNIQUE (company_id, source_system, source_schema, source_table, source_id)
);

CREATE TABLE IF NOT EXISTS {schema}.party_source_links (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio          text UNIQUE NOT NULL,
  company_id     text NOT NULL,
  party_id       uuid REFERENCES {schema}.parties(id) ON DELETE CASCADE,
  source_system  text NOT NULL,
  source_schema  text NOT NULL,
  source_table   text NOT NULL,
  source_id      text NOT NULL,
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now(),
  metadata       jsonb DEFAULT '{}',
  UNIQUE (company_id, source_system, source_schema, source_table, source_id)
);

CREATE TABLE IF NOT EXISTS {schema}.supplier_product_mappings (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio                       text UNIQUE NOT NULL,
  company_id                  text NOT NULL,
  supplier_party_id           uuid REFERENCES {schema}.parties(id),
  supplier_rfc                text,
  supplier_product_key        text,
  supplier_product_description text,
  sat_product_key             text,
  sat_unit_key                text,
  factu4all_product_id        uuid REFERENCES {schema}.products(id),
  confidence                  numeric(5,4),
  status                      text DEFAULT 'unmapped',
  created_at                  timestamptz DEFAULT now(),
  updated_at                  timestamptz DEFAULT now(),
  metadata                    jsonb DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS {schema}.secrets_vault (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id     text NOT NULL,
  scope_type     text NOT NULL,
  scope_ref      text NOT NULL DEFAULT '',
  dek_encrypted  text NOT NULL,
  nonce_dek      text NOT NULL,
  kek_version    int NOT NULL DEFAULT 1,
  payload_cifrado jsonb NOT NULL,
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now(),
  UNIQUE (company_id, scope_type, scope_ref)
);

CREATE INDEX IF NOT EXISTS idx_factu4all_pac_accounts_company ON {schema}.pac_accounts(company_id);
CREATE INDEX IF NOT EXISTS idx_factu4all_issuer_profiles_company ON {schema}.issuer_profiles(company_id, rfc);
CREATE INDEX IF NOT EXISTS idx_factu4all_folio_series_company ON {schema}.folio_series(company_id, cfdi_type, environment);
CREATE INDEX IF NOT EXISTS idx_factu4all_parties_company ON {schema}.parties(company_id, party_type, rfc);
CREATE INDEX IF NOT EXISTS idx_factu4all_products_company ON {schema}.products(company_id, sat_product_key);
CREATE INDEX IF NOT EXISTS idx_factu4all_products_source_key ON {schema}.products(company_id, source_product_key);
CREATE INDEX IF NOT EXISTS idx_factu4all_cfdi_documents_company ON {schema}.cfdi_documents(company_id, status);
CREATE INDEX IF NOT EXISTS idx_factu4all_cfdi_documents_source ON {schema}.cfdi_documents(company_id, source_system, source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_factu4all_cfdi_item_movements_doc ON {schema}.cfdi_item_movements(cfdi_document_id);
CREATE INDEX IF NOT EXISTS idx_factu4all_cfdi_item_movements_product ON {schema}.cfdi_item_movements(company_id, product_id);
CREATE INDEX IF NOT EXISTS idx_factu4all_document_files_doc ON {schema}.document_files(cfdi_document_id);
CREATE INDEX IF NOT EXISTS idx_factu4all_supplier_mappings_company ON {schema}.supplier_product_mappings(company_id, status);
CREATE INDEX IF NOT EXISTS idx_factu4all_product_stock_lookup ON {schema}.product_stock(company_id, product_id, environment);

GRANT USAGE ON SCHEMA {schema} TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA {schema}
  GRANT ALL ON TABLES TO anon, authenticated, service_role;

-- secrets_vault guarda credenciales cifradas: solo service_role (nuestros
-- skills usan siempre la service role key). anon/authenticated nunca deben
-- poder leer ni la fila cifrada via PostgREST directo.
REVOKE ALL ON {schema}.secrets_vault FROM anon, authenticated;
"""

_TABLES = [
    "factu4all_company_settings",
    "pac_accounts",
    "issuer_profiles",
    "folio_series",
    "parties",
    "products",
    "cfdi_documents",
    "cfdi_item_movements",
    "document_files",
    "source_catalogs",
    "product_source_links",
    "party_source_links",
    "supplier_product_mappings",
    "secrets_vault",
    "product_stock",
]


class Factu4AllSchemaSetupService:
    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", True)
        schema = self._resolve_schema(context)
        if not schema:
            return {"ok": False, "error": "schema requerido en context o env FACTU4ALL_SCHEMA"}
        sql = _DDL.strip().replace("{schema}", schema)

        if dry_run:
            return {"ok": True, "message": "dry_run — SQL no ejecutado", "data": {"schema": schema, "sql": sql, "tables": _TABLES}}

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
                    "tables": _TABLES,
                    "note": "Exponer el schema en Supabase Dashboard -> Settings -> API -> Exposed schemas",
                },
            }
        except Exception as exc:
            return {"ok": False, "error": f"Error ejecutando DDL: {exc}"}

    def _resolve_schema(self, context: dict) -> str | None:
        return str(context.get("schema") or context.get("supabase_schema") or os.getenv("FACTU4ALL_SCHEMA", "") or "").strip() or None

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
