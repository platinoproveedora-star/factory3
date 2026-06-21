from __future__ import annotations
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from _statement_common import _VERTICAL_ROOT

_VALID_NAME = re.compile(r"^[a-z][a-z0-9_]{2,50}$")


class BankStatementProfileLearnService:
    def ejecutar(self, context: dict) -> dict:
        bank_profile = str(context.get("bank_profile") or "").strip().lower()
        profile_version = str(context.get("profile_version") or "v1").strip()
        bank_name = str(context.get("bank_name") or bank_profile).strip()
        column_mapping: dict = context.get("column_mapping") or {}
        detect_markers: list = context.get("detect_markers") or []

        if not _VALID_NAME.match(bank_profile):
            return {"ok": False, "error": "bank_profile invalido (solo minusculas, numeros y guion bajo, min 3 chars)"}
        if not column_mapping:
            return {"ok": False, "error": "column_mapping requerido"}

        profile = {
            "bank_profile": bank_profile,
            "profile_version": profile_version,
            "profile_status": "borrador",
            "bank_name": bank_name,
            "detect_markers": detect_markers,
            "anchor_regex": column_mapping.get("anchor_regex", ""),
            "date_format": column_mapping.get("date_format", ""),
            "amount_strategy": column_mapping.get("amount_strategy", ""),
            "rastreo_regex": column_mapping.get("rastreo_regex", ""),
            "referencia_regex": column_mapping.get("referencia_regex", ""),
            "summary_deposits_regex": column_mapping.get("summary_deposits_regex", ""),
            "summary_withdrawals_regex": column_mapping.get("summary_withdrawals_regex", ""),
            "skip_line_patterns": column_mapping.get("skip_line_patterns", []),
        }
        if column_mapping.get("date_locale_fix"):
            profile["date_locale_fix"] = column_mapping["date_locale_fix"]
        if column_mapping.get("cargo_x_max"):
            profile["cargo_x_max"] = column_mapping["cargo_x_max"]
        if column_mapping.get("abono_x_min"):
            profile["abono_x_min"] = column_mapping["abono_x_min"]

        dry_run = bool(context.get("dry_run", True))
        profile_path = _VERTICAL_ROOT / "profiles" / f"{bank_profile}.{profile_version}.profile.json"

        if profile_path.exists() and not context.get("overwrite"):
            return {"ok": False, "error": f"perfil {profile_path.name} ya existe. Pasa overwrite=true para sobreescribir."}

        if not dry_run:
            profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "ok": True,
            "data": {
                "profile_path": str(profile_path.relative_to(Path.cwd())) if not dry_run else str(profile_path),
                "status": "borrador",
                "dry_run": dry_run,
                "profile": profile,
            },
        }
