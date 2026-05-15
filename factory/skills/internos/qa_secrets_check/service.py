"""Verifica env vars y secrets requeridos por empresa/campaña."""
from __future__ import annotations

import os

# Secrets por categoría — se pueden sobreescribir vía context
_SECRETS_BY_CATEGORY = {
    "core": [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "ANTHROPIC_API_KEY",
    ],
    "meta_ads": [
        "META_ACCESS_TOKEN",
        "META_APP_ID",
        "META_APP_SECRET",
        "META_PAGE_ID",
        "META_AD_ACCOUNT_ID",
    ],
    "telegram": [
        "FACTORY3_ADMIN_BOT_TOKEN",
    ],
    "render": [
        "RENDER_API_KEY",
        "RENDER_OWNER_ID",
    ],
    "github": [
        "GITHUB_TOKEN",
    ],
    "supabase_mgmt": [
        "SUPABASE_ACCESS_TOKEN",
        "SUPABASE_PROJECT_REF",
    ],
    "openai": [
        "OPENAI_API_KEY",
    ],
}

_SEMAFORO = {"ok": "OK", "error": "ERROR", "warning": "WARN"}


class QASecretsCheckService:

    def ejecutar(self, context: dict) -> dict:
        company_id   = context.get("company_id", "")
        categories   = context.get("categories") or list(_SECRETS_BY_CATEGORY.keys())
        extra_vars   = context.get("extra_vars") or []  # vars adicionales por empresa

        if isinstance(categories, str):
            categories = [c.strip() for c in categories.split(",")]

        required: list[str] = []
        for cat in categories:
            if cat in _SECRETS_BY_CATEGORY:
                required.extend(_SECRETS_BY_CATEGORY[cat])
            else:
                required.append(cat)  # soporte directo por nombre de var
        required.extend(extra_vars)

        results: list[dict] = []
        missing: list[str] = []
        present: list[str] = []

        for var in required:
            val = os.getenv(var, "")
            if not val:
                missing.append(var)
                results.append({
                    "var": var,
                    "status": "error",
                    "semaforo": "ERROR",
                    "detalle": "ausente o vacía",
                })
            else:
                # Nunca exponer el valor — solo longitud como confirmación
                present.append(var)
                results.append({
                    "var": var,
                    "status": "ok",
                    "semaforo": "OK",
                    "detalle": f"presente ({len(val)} chars)",
                })

        ok = len(missing) == 0
        return {
            "ok": ok,
            "message": (
                f"Todos los secrets OK ({len(present)} vars)"
                if ok
                else f"{len(missing)} secrets faltantes: {', '.join(missing)}"
            ),
            "data": {
                "company_id": company_id,
                "categories": categories,
                "total": len(results),
                "presentes": len(present),
                "faltantes": len(missing),
                "missing_vars": missing,
                "checks": results,
            },
        }

    @staticmethod
    def categorias_disponibles() -> list[str]:
        return list(_SECRETS_BY_CATEGORY.keys())
