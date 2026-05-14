from __future__ import annotations

import json
import re
from pathlib import Path


_VALID_COMPANY_ID = re.compile(r"^[A-Z][A-Z0-9_]*$")


class CompanyConfigLoaderService:
    """Loads a company config from companies/<COMPANY_ID>/company.config.json."""

    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        config_path_raw = str(context.get("config_path") or "").strip()

        if not company_id and not config_path_raw:
            return {"ok": False, "error": "company_id o config_path requerido"}
        if company_id and not _VALID_COMPANY_ID.match(company_id):
            return {"ok": False, "error": "company_id debe usar MAYUSCULAS, numeros y _"}

        root = Path(__file__).resolve().parents[5]
        companies_root = root / "companies"
        config_path = self._resolve_config_path(companies_root, company_id, config_path_raw)
        if isinstance(config_path, dict):
            return config_path

        if not config_path.exists():
            return {"ok": False, "error": f"config no encontrada: {config_path}"}

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"company.config.json invalido: {exc}"}

        if not isinstance(data, dict):
            return {"ok": False, "error": "company.config.json debe contener un objeto JSON"}

        configured_id = str(data.get("company_id") or "").strip()
        if company_id and configured_id and configured_id != company_id:
            return {"ok": False, "error": f"company_id no coincide: {configured_id} != {company_id}"}

        data.setdefault("company_id", company_id or configured_id or config_path.parent.name)
        return {
            "ok": True,
            "data": {
                "company_id": data["company_id"],
                "company_dir": str(config_path.parent),
                "config_path": str(config_path),
                "config": data,
            },
        }

    def _resolve_config_path(self, companies_root: Path, company_id: str, config_path_raw: str) -> Path | dict:
        if config_path_raw:
            candidate = Path(config_path_raw)
            if not candidate.is_absolute():
                candidate = companies_root.parent / candidate
            try:
                resolved = candidate.resolve()
                root = companies_root.parent.resolve()
                resolved.relative_to(root)
            except ValueError:
                return {"ok": False, "error": "config_path debe estar dentro del workspace"}
            return resolved

        return companies_root / company_id / "company.config.json"
