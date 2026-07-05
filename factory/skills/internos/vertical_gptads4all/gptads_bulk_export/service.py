from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path

from factory.engine import SupabaseClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gptads_common import FORMATS, clean_text, safe_filename  # noqa: E402


class GptAdsBulkExportService:
    def ejecutar(self, context: dict) -> dict:
        campaign_draft = context.get("campaign_draft") if isinstance(context.get("campaign_draft"), dict) else {}
        creative_set = context.get("creative_set") if isinstance(context.get("creative_set"), dict) else {}
        intent_set = context.get("intent_set") if isinstance(context.get("intent_set"), dict) else {}
        context_hint_set = context.get("context_hint_set") if isinstance(context.get("context_hint_set"), dict) else {}
        campaign_key = clean_text(campaign_draft.get("campaign_key") or creative_set.get("campaign_key"))
        fmt = clean_text(context.get("format") or "csv").lower()
        if fmt not in FORMATS:
            return {"ok": False, "error": "format invalido"}
        if not campaign_key:
            return {"ok": False, "error": "campaign_key required"}

        rows = self._rows(campaign_draft, creative_set, intent_set, context_hint_set)
        generated_at = datetime.utcnow().isoformat() + "Z"
        warnings = []
        dry_run = context.get("dry_run", True)
        if dry_run:
            warnings.append("dry_run_no_file_written")

        artifacts = []
        content_by_format = {}
        formats = ["csv", "json"] if fmt == "both" else [fmt]
        output_dir = Path(context.get("output_dir") or "/tmp/gptads_exports")
        basename = safe_filename(campaign_key)

        for one_format in formats:
            if one_format == "csv":
                content = self._csv(rows)
                suffix = "csv"
            else:
                content = json.dumps(
                    {
                        "campaign_draft": campaign_draft,
                        "creative_set": creative_set,
                        "intent_set": intent_set,
                        "context_hint_set": context_hint_set,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                suffix = "json"
            content_by_format[one_format] = content
            file_path = None
            if not dry_run:
                try:
                    output_dir.mkdir(parents=True, exist_ok=True)
                    path = output_dir / f"{basename}.{suffix}"
                    path.write_text(content, encoding="utf-8")
                    file_path = str(path)
                except Exception:
                    return {"ok": False, "error": "file_write_failed"}
            artifacts.append({"format": one_format, "file_path": file_path, "rows_exported": len(rows)})

        export_artifact = {
            "campaign_key": campaign_key,
            "format": fmt,
            "artifacts": artifacts,
            "generated_at": generated_at,
        }

        persist_db = bool(context.get("persist_db", True))
        if not dry_run and persist_db:
            empresa_id = clean_text(campaign_draft.get("empresa_id") or context.get("empresa_id") or context.get("company_id"))
            ctx = dict(context)
            schema = clean_text(ctx.get("schema") or ctx.get("supabase_schema") or ctx.get("db_schema"))
            if not schema:
                return {"ok": False, "error": "schema required for write", "data": {"export_artifact": export_artifact, "warnings": warnings}}
            ctx["schema"] = schema
            ctx["company_id"] = empresa_id
            try:
                db_rows = [
                    {
                        "empresa_id": empresa_id,
                        "campaign_key": campaign_key,
                        "format": item["format"],
                        "file_path": item["file_path"],
                        "rows_exported": item["rows_exported"],
                        "generated_at": generated_at,
                    }
                    for item in artifacts
                ]
                result = SupabaseClient(ctx).rest_insert("exports", db_rows)
                if not result.get("ok"):
                    warnings.append("db_failed_after_file_write")
                    return {"ok": False, "error": "db_persistence_failed", "data": {"export_artifact": export_artifact, "warnings": warnings}}
            except Exception:
                warnings.append("db_failed_after_file_write")
                return {"ok": False, "error": "db_persistence_failed", "data": {"export_artifact": export_artifact, "warnings": warnings}}
        elif not dry_run:
            warnings.append("db_persistence_skipped")

        return {"ok": True, "data": {"export_artifact": export_artifact, "warnings": warnings, "content": content_by_format if dry_run else None}}

    def _rows(self, campaign_draft: dict, creative_set: dict, intent_set: dict, context_hint_set: dict) -> list[dict]:
        intents = {item.get("intent_id"): item for item in intent_set.get("intents", []) if isinstance(item, dict)}
        hints_by_intent: dict[str, list] = {}
        for hint in context_hint_set.get("hints", []) if isinstance(context_hint_set.get("hints"), list) else []:
            if isinstance(hint, dict):
                hints_by_intent.setdefault(hint.get("intent_id"), []).append(hint)
        rows = []
        for creative in creative_set.get("creatives", []) if isinstance(creative_set.get("creatives"), list) else []:
            if not isinstance(creative, dict):
                continue
            intent_id = creative.get("intent_id")
            intent = intents.get(intent_id, {})
            hints = hints_by_intent.get(intent_id, [])
            rows.append(
                {
                    "campaign_key": campaign_draft.get("campaign_key"),
                    "campaign_name": campaign_draft.get("campaign_name"),
                    "product_key": campaign_draft.get("product_key"),
                    "intent_id": intent_id,
                    "intent_text": intent.get("intent_text"),
                    "hint_ids": "|".join(clean_text(h.get("hint_id")) for h in hints),
                    "hint_texts": "|".join(clean_text(h.get("hint_text")) for h in hints),
                    "creative_id": creative.get("creative_id"),
                    "variant": creative.get("variant"),
                    "headline": creative.get("headline"),
                    "body": creative.get("body"),
                    "cta": creative.get("cta"),
                }
            )
        return rows

    def _csv(self, rows: list[dict]) -> str:
        headers = [
            "campaign_key",
            "campaign_name",
            "product_key",
            "intent_id",
            "intent_text",
            "hint_ids",
            "hint_texts",
            "creative_id",
            "variant",
            "headline",
            "body",
            "cta",
        ]
        handle = StringIO()
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in headers})
        return handle.getvalue()
