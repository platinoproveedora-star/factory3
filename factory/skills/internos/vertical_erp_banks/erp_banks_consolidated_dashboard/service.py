from __future__ import annotations

import importlib.util
from pathlib import Path


class ErpBanksConsolidatedDashboardService:
    def ejecutar(self, context: dict) -> dict:
        contexts = context.get("contexts")
        if not isinstance(contexts, list) or not contexts:
            return {"ok": False, "error": "contexts requerido como lista"}

        resolver = self._load_service("vertical_erp", "erp_project_context_resolve", "ErpProjectContextResolveService")
        account_list = self._load_service("vertical_erp_banks", "erp_banks_account_list", "ErpBanksAccountListService")

        by_empresa = []
        total_by_currency: dict[str, float] = {}
        total_by_account_type: dict[str, float] = {}
        warnings: list[str] = []

        for raw_ctx in contexts:
            if not isinstance(raw_ctx, dict):
                warnings.append("context invalido omitido")
                continue
            resolved = resolver.ejecutar({**raw_ctx, "module_code": raw_ctx.get("module_code") or "banks"})
            if not resolved.get("ok"):
                warnings.append(resolved.get("error") or f"contexto invalido: {raw_ctx}")
                continue
            data = resolved.get("data") or {}
            list_result = account_list.ejecutar(
                {
                    **raw_ctx,
                    "company_id": data.get("company_id"),
                    "empresa_id": data.get("empresa_id") or data.get("company_id"),
                    "project_code": data.get("project_code"),
                    "module_code": data.get("module_code") or "banks",
                    "schema": data.get("schema"),
                    "limit": raw_ctx.get("limit") or 500,
                }
            )
            if not list_result.get("ok"):
                warnings.append(list_result.get("error") or f"no se pudieron leer cuentas para {data.get('company_id')}")
                continue
            accounts = (list_result.get("data") or {}).get("accounts") or []
            empresa_currency: dict[str, float] = {}
            for account in accounts:
                currency = str(account.get("currency") or "MXN")
                account_type = str(account.get("account_type") or "other")
                balance = round(float(account.get("current_balance") or 0), 2)
                empresa_currency[currency] = round(empresa_currency.get(currency, 0) + balance, 2)
                total_by_currency[currency] = round(total_by_currency.get(currency, 0) + balance, 2)
                total_by_account_type[account_type] = round(total_by_account_type.get(account_type, 0) + balance, 2)
            by_empresa.append(
                {
                    "company_id": data.get("company_id"),
                    "project_code": data.get("project_code"),
                    "schema": data.get("schema"),
                    "total_by_currency": empresa_currency,
                    "accounts": accounts,
                }
            )

        return {
            "ok": True,
            "data": {
                "by_empresa": by_empresa,
                "total_by_currency": total_by_currency,
                "total_by_account_type": total_by_account_type,
                "warnings": warnings,
            },
        }

    def _load_service(self, vertical: str, skill: str, class_name: str):
        path = Path(__file__).resolve().parents[2] / vertical / skill / "service.py"
        spec = importlib.util.spec_from_file_location(f"{skill}_service", path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return getattr(module, class_name)()
