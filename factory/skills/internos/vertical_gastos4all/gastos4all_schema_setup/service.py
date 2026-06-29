"""Crea el schema gastos4all multi-tenant en Supabase (Management API)."""
from __future__ import annotations
import json
import os
import urllib.request


_DDL = """
CREATE SCHEMA IF NOT EXISTS gastos4all;

CREATE TABLE IF NOT EXISTS gastos4all.categorias_gasto (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text UNIQUE NOT NULL,
  nombre       text NOT NULL,
  activo       boolean DEFAULT true,
  empresa_id   text NOT NULL,
  project_code text,
  module_code  text
);

CREATE TABLE IF NOT EXISTS gastos4all.usuarios (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio            text UNIQUE NOT NULL,
  nombre           text NOT NULL,
  telegram_chat_id text,
  rol              text DEFAULT 'viewer',
  empresa_id       text NOT NULL,
  project_code     text,
  module_code      text
);

CREATE TABLE IF NOT EXISTS gastos4all.gastos (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio             text UNIQUE NOT NULL,
  fecha             date NOT NULL,
  monto             numeric(12,2) NOT NULL DEFAULT 0,
  descripcion       text,
  metodo_captura    text DEFAULT 'dashboard',
  vehiculo          text,
  categoria_id      uuid REFERENCES gastos4all.categorias_gasto(id),
  usuario_id        uuid REFERENCES gastos4all.usuarios(id),
  cta_retiro_id     uuid,
  cta_retiro_folio  text,
  cta_retiro_nombre text,
  empresa_id        text NOT NULL,
  project_code      text,
  module_code       text,
  erp_tags          jsonb DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS gastos4all.gasto_eventos (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text UNIQUE NOT NULL,
  gasto_id     uuid REFERENCES gastos4all.gastos(id),
  usuario_id   uuid,
  evento       text NOT NULL,
  detalle      jsonb DEFAULT '{}',
  created_at   timestamptz DEFAULT now(),
  empresa_id   text NOT NULL,
  project_code text,
  module_code  text
);

CREATE TABLE IF NOT EXISTS gastos4all.gasto_documentos (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text UNIQUE NOT NULL,
  gasto_id     uuid REFERENCES gastos4all.gastos(id),
  tipo         text,
  storage_path text,
  empresa_id   text NOT NULL,
  created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_g4all_gastos_empresa    ON gastos4all.gastos(empresa_id);
CREATE INDEX IF NOT EXISTS idx_g4all_gastos_fecha      ON gastos4all.gastos(fecha);
CREATE INDEX IF NOT EXISTS idx_g4all_categorias_empresa ON gastos4all.categorias_gasto(empresa_id);
CREATE INDEX IF NOT EXISTS idx_g4all_usuarios_empresa  ON gastos4all.usuarios(empresa_id);
CREATE INDEX IF NOT EXISTS idx_g4all_eventos_empresa   ON gastos4all.gasto_eventos(empresa_id);
"""


class Gastos4AllSchemaSetupService:

    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", True)

        if dry_run:
            return {"ok": True, "message": "dry_run — SQL no ejecutado", "data": {"sql": _DDL.strip()}}

        project_ref = self._project_ref()
        if not project_ref:
            return {"ok": False, "error": "No se pudo obtener SUPABASE_PROJECT_REF. Configúralo o expón SUPABASE_URL como https://<ref>.supabase.co"}

        token = os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()
        if not token:
            return {"ok": False, "error": "SUPABASE_ACCESS_TOKEN requerido para crear schema"}

        try:
            self._run_sql(project_ref, token, _DDL.strip())
            return {
                "ok": True,
                "message": "Schema gastos4all creado correctamente",
                "data": {
                    "schema": "gastos4all",
                    "tables": ["categorias_gasto", "usuarios", "gastos", "gasto_eventos", "gasto_documentos"],
                    "note": "Exponer el schema en Supabase Dashboard → Settings → API → Exposed schemas",
                },
            }
        except Exception as exc:
            return {"ok": False, "error": f"Error ejecutando DDL: {exc}"}

    def _project_ref(self) -> str:
        ref = os.getenv("SUPABASE_PROJECT_REF", "").strip()
        if ref:
            return ref
        url = os.getenv("SUPABASE_URL", "").strip()
        if url:
            host = url.replace("https://", "").replace("http://", "").split(".")[0]
            return host
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
