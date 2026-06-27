"""Persiste solicitudes SAT en Supabase para reutilizarlas entre sesiones."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_ESTADOS = {1: "Aceptada", 2: "En proceso", 3: "Terminada",
            4: "Error", 5: "Rechazada", 6: "Vencida", 0: "Pendiente"}

_DDL = """
CREATE TABLE IF NOT EXISTS {schema}.sat_solicitudes (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id     text NOT NULL,
  rfc            text NOT NULL,
  id_solicitud   text UNIQUE NOT NULL,
  tipo           text NOT NULL DEFAULT 'E',
  tipo_solicitud text NOT NULL DEFAULT 'CFDI',
  fecha_inicio   date NOT NULL,
  fecha_fin      date NOT NULL,
  estado         int  DEFAULT 1,
  paquetes       jsonb DEFAULT '[]'::jsonb,
  num_cfdis      int  DEFAULT 0,
  created_at     timestamptz DEFAULT now(),
  updated_at     timestamptz DEFAULT now()
);

GRANT USAGE ON SCHEMA {schema} TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA {schema}
  GRANT ALL ON TABLES TO anon, authenticated, service_role;
"""


class SatSolicitudManagerService:

    def ejecutar(self, context: dict) -> dict:
        action = context.get("action", "list")
        schema = context.get("schema") or os.getenv("SUPABASE_SCHEMA", "uc102_proy001")

        if action == "setup":
            return self._setup(schema, context)
        if action == "save":
            return self._save(schema, context)
        if action == "list":
            return self._list(schema, context)
        if action == "update_estado":
            return self._update_estado(schema, context)
        return {"ok": False, "error": f"Acción desconocida: {action}"}

    # ── setup ──────────────────────────────────────────────────────────────

    def _setup(self, schema: str, context: dict) -> dict:
        sql = _DDL.format(schema=schema)
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"sql": sql}}

        access_token = (context.get("supabase_access_token") or
                        os.getenv("SUPABASE_ACCESS_TOKEN", "")).strip()
        project_ref  = self._project_ref(context)
        if not access_token or not project_ref:
            return {"ok": False, "error": "Faltan SUPABASE_ACCESS_TOKEN / SUPABASE_PROJECT_REF",
                    "data": {"sql_manual": sql}}

        endpoint = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps({"query": sql}).encode(),
            headers={"Authorization": f"Bearer {access_token}",
                     "Content-Type": "application/json",
                     "User-Agent": "FactoryFactory/0.1 (+https://github.com/)"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                r.read()
            return {"ok": True, "message": f"Tabla sat_solicitudes creada en {schema}"}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Management API {e.code}: {body[:300]}"}

    # ── save ───────────────────────────────────────────────────────────────

    def _save(self, schema: str, context: dict) -> dict:
        url, key = self._supabase()
        if not url:
            return {"ok": False, "error": "Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY"}

        required = ["empresa_id", "rfc", "id_solicitud", "tipo", "fecha_inicio", "fecha_fin"]
        missing  = [f for f in required if not context.get(f)]
        if missing:
            return {"ok": False, "error": f"Faltan campos: {missing}"}

        row = {
            "empresa_id":     context["empresa_id"],
            "rfc":            context["rfc"],
            "id_solicitud":   context["id_solicitud"],
            "tipo":           context.get("tipo", "E"),
            "tipo_solicitud": context.get("tipo_solicitud", "CFDI"),
            "fecha_inicio":   context["fecha_inicio"],
            "fecha_fin":      context["fecha_fin"],
            "estado":         int(context.get("estado", 1)),
            "paquetes":       json.dumps(context.get("paquetes", [])),
            "num_cfdis":      int(context.get("num_cfdis", 0)),
            "updated_at":     "now()",
        }

        endpoint = f"{url}/rest/v1/sat_solicitudes"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(row).encode(),
            headers={**self._headers(key, schema),
                     "Prefer": "resolution=merge-duplicates,return=minimal"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                r.read()
            return {"ok": True, "message": f"Solicitud {context['id_solicitud']} guardada"}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase {e.code}: {body[:200]}"}

    # ── update_estado ──────────────────────────────────────────────────────

    def _update_estado(self, schema: str, context: dict) -> dict:
        url, key = self._supabase()
        if not url:
            return {"ok": False, "error": "Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY"}

        id_sol = context.get("id_solicitud", "")
        if not id_sol:
            return {"ok": False, "error": "Falta id_solicitud"}

        patch = {
            "estado":     int(context.get("estado", 1)),
            "paquetes":   json.dumps(context.get("paquetes", [])),
            "num_cfdis":  int(context.get("num_cfdis", 0)),
            "updated_at": "now()",
        }
        endpoint = f"{url}/rest/v1/sat_solicitudes?id_solicitud=eq.{id_sol}"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(patch).encode(),
            headers={**self._headers(key, schema), "Prefer": "return=minimal"},
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                r.read()
            return {"ok": True, "message": f"Estado actualizado: {id_sol}"}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase {e.code}: {body[:200]}"}

    # ── list ───────────────────────────────────────────────────────────────

    def _list(self, schema: str, context: dict) -> dict:
        url, key = self._supabase()
        if not url:
            return {"ok": False, "error": "Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY"}

        empresa_id = context.get("empresa_id") or os.getenv("EMPRESA_ID", "")
        rfc        = context.get("rfc") or os.getenv("SAT_RFC", "")
        params     = []
        if empresa_id:
            params.append(f"empresa_id=eq.{empresa_id}")
        if rfc:
            params.append(f"rfc=eq.{rfc}")
        if context.get("tipo"):
            params.append(f"tipo=eq.{context['tipo']}")
        # excluir vencidas por defecto
        if not context.get("incluir_vencidas"):
            params.append("estado=neq.6")

        qs = "&".join(params) + "&order=created_at.desc&limit=50"
        endpoint = f"{url}/rest/v1/sat_solicitudes?{qs}"
        req = urllib.request.Request(
            endpoint,
            headers={**self._headers(key, schema), "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                rows = json.loads(r.read().decode())
            # enriquecer con texto de estado
            for row in rows:
                row["estado_txt"] = _ESTADOS.get(row.get("estado", 0), "?")
                if isinstance(row.get("paquetes"), str):
                    row["paquetes"] = json.loads(row["paquetes"])
            return {"ok": True, "message": f"{len(rows)} solicitudes",
                    "data": {"solicitudes": rows, "total": len(rows)}}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase {e.code}: {body[:200]}"}

    # ── helpers ────────────────────────────────────────────────────────────

    def _supabase(self):
        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        return (url, key) if url and key else ("", "")

    def _headers(self, key: str, schema: str) -> dict:
        return {
            "apikey":          key,
            "Authorization":   f"Bearer {key}",
            "Content-Type":    "application/json",
            "Content-Profile": schema,
            "Accept-Profile":  schema,
            "User-Agent":      "FactoryFactory/0.1 (+https://github.com/)",
        }

    def _project_ref(self, context: dict) -> str:
        ref = (context.get("supabase_project_ref") or
               os.getenv("SUPABASE_PROJECT_REF", "")).strip()
        if not ref:
            import re
            m = re.search(r"https://([^.]+)\.supabase\.co",
                          os.getenv("SUPABASE_URL", ""))
            ref = m.group(1) if m else ""
        return ref
