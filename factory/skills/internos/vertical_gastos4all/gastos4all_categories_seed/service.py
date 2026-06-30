"""Siembra categorías de gasto default para una empresa nueva."""
from __future__ import annotations
import json
import os
import urllib.request


_CATEGORIAS_DEFAULT = [
    "combustible",
    "taller y mantenimiento",
    "nomina",
    "recargas celulares",
    "gastos varios",
    "alimentacion",
    "hospedaje",
    "peajes y casetas",
    "refacciones",
    "papeleria",
    "servicios",
    "otros",
]

_SCHEMA = "gastos4all"


class Gastos4AllCategoriesSeedService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = str(context.get("empresa_id") or context.get("company_id") or "").strip()
        dry_run    = context.get("dry_run", True)

        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}

        if dry_run:
            return {"ok": True, "message": "dry_run", "data": {"empresa_id": empresa_id, "categorias": _CATEGORIAS_DEFAULT}}

        try:
            existing = self._get_existing(empresa_id)
            existing_names = {r["nombre"] for r in existing}
            to_insert = [c for c in _CATEGORIAS_DEFAULT if c not in existing_names]

            if not to_insert:
                return {"ok": True, "message": "Categorías ya existían", "data": {"empresa_id": empresa_id, "insertadas": 0}}

            rows = []
            for i, nombre in enumerate(to_insert):
                rows.append({
                    "folio": await_next_folio := f"CAT-{str(i + len(existing) + 1).zfill(3)}",
                    "nombre": nombre,
                    "activo": True,
                    "empresa_id": empresa_id,
                })

            self._insert(rows)
            return {"ok": True, "message": "Categorías sembradas", "data": {"empresa_id": empresa_id, "insertadas": len(rows), "categorias": [r["nombre"] for r in rows]}}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _headers(self, write: bool = False) -> dict:
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY no configurada")
        h = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept-Profile": _SCHEMA,
            "Content-Type": "application/json",
        }
        if write:
            h["Content-Profile"] = _SCHEMA
            h["Prefer"] = "return=representation"
        return h

    def _base(self) -> str:
        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        if not url:
            raise RuntimeError("SUPABASE_URL no configurada")
        return f"{url}/rest/v1"

    def _get_existing(self, empresa_id: str) -> list:
        qs = f"empresa_id=eq.{empresa_id}&select=nombre&limit=200"
        req = urllib.request.Request(f"{self._base()}/categorias_gasto?{qs}", headers=self._headers())
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read() or b"[]")

    def _insert(self, rows: list) -> None:
        data = json.dumps(rows).encode()
        req = urllib.request.Request(
            f"{self._base()}/categorias_gasto",
            data=data,
            headers=self._headers(write=True),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
