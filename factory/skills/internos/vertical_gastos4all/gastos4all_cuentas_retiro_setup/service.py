"""Crea tabla cuentas_retiro en schema gastos4all (DDL via Management API)."""
from __future__ import annotations
import json
import os
import urllib.request


_DDL = """
CREATE TABLE IF NOT EXISTS gastos4all.cuentas_retiro (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text UNIQUE NOT NULL,
  nombre       text NOT NULL,
  banco        text,
  numero_mask  text,
  tipo         text DEFAULT 'cuenta_corriente',
  activo       boolean DEFAULT true,
  empresa_id   text NOT NULL,
  project_code text,
  module_code  text,
  created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_g4all_cuentas_empresa ON gastos4all.cuentas_retiro(empresa_id);
"""


class Gastos4AllCuentasRetiroSetupService:

    def ejecutar(self, context: dict) -> dict:
        dry_run = context.get("dry_run", True)

        if dry_run:
            return {"ok": True, "message": "dry_run — DDL no ejecutado", "data": {"sql": _DDL.strip()}}

        project_ref = self._project_ref()
        if not project_ref:
            return {"ok": False, "error": "No se pudo obtener SUPABASE_PROJECT_REF"}

        token = os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()
        if not token:
            return {"ok": False, "error": "SUPABASE_ACCESS_TOKEN requerido"}

        try:
            self._run_sql(project_ref, token, _DDL.strip())
            return {
                "ok": True,
                "message": "Tabla cuentas_retiro creada en schema gastos4all",
                "data": {"table": "gastos4all.cuentas_retiro", "columns": ["id", "folio", "nombre", "banco", "numero_mask", "tipo", "activo", "empresa_id"]},
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _project_ref(self) -> str:
        ref = os.getenv("SUPABASE_PROJECT_REF", "").strip()
        if ref:
            return ref
        url = os.getenv("SUPABASE_URL", "").strip()
        if url:
            return url.replace("https://", "").replace("http://", "").split(".")[0]
        return ""

    def _run_sql(self, project_ref: str, token: str, sql: str) -> None:
        payload = json.dumps({"query": sql}).encode()
        req = urllib.request.Request(
            f"https://api.supabase.com/v1/projects/{project_ref}/database/query",
            data=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "FactoryFactory/0.1 (+https://github.com/)"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
