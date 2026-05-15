from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class CampaignConfigWriterService:
    """Write normalized campaign runtime config into a company campaign JSON."""

    ALLOWED_FIELDS = {
        "landing_url",
        "link",
        "image_url",
        "privacy_url",
        "whatsapp_number",
        "approver",
        "daily_budget",
        "total_budget",
        "days",
        "meta_ad_account_id",
        "meta_page_id",
        "meta_app_id",
        "form_id",
        "campaign_id",
        "adset_id",
        "creative_id",
        "ad_id",
        "status",
        "notes",
    }

    def ejecutar(self, context: dict) -> dict:
        root = Path(__file__).resolve().parents[5]
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        campaign_slug = str(context.get("campaign_slug") or context.get("slug") or "").strip()
        campaign_path = context.get("campaign_path") or context.get("path")
        dry_run = bool(context.get("dry_run", True))

        path_result = self._resolve_path(root, company_id, campaign_slug, campaign_path)
        if not path_result.get("ok"):
            return path_result
        path = path_result["path"]

        if not path.exists():
            return {"ok": False, "error": f"campaign JSON no existe: {path}"}

        try:
            original = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"JSON invalido en {path}: {exc}"}

        updates = self._collect_updates(context)
        if not updates:
            return {"ok": False, "error": "sin campos validos para actualizar"}

        updated = self._apply_updates(original, updates)
        updated.setdefault("ops", {})
        updated["ops"]["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated["ops"]["updated_by"] = context.get("updated_by") or "campaign_config_writer"

        if not dry_run:
            path.write_text(json.dumps(updated, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

        return {
            "ok": True,
            "data": {
                "campaign_path": str(path),
                "dry_run": dry_run,
                "updated_fields": sorted(updates),
                "config": updated,
            },
        }

    def _resolve_path(self, root: Path, company_id: str, campaign_slug: str, campaign_path: str | None) -> dict:
        if campaign_path:
            path = Path(campaign_path)
            if not path.is_absolute():
                path = root / path
        else:
            if not company_id:
                return {"ok": False, "error": "company_id requerido si no pasas campaign_path"}
            if not campaign_slug:
                return {"ok": False, "error": "campaign_slug requerido si no pasas campaign_path"}
            path = root / "companies" / company_id / f"{campaign_slug}.json"

        try:
            path.relative_to(root)
        except ValueError:
            return {"ok": False, "error": "campaign_path debe estar dentro del repo"}
        return {"ok": True, "path": path}

    def _collect_updates(self, context: dict) -> dict:
        updates = {}
        incoming = context.get("updates") if isinstance(context.get("updates"), dict) else {}
        for source in (incoming, context):
            for key, value in source.items():
                if key in self.ALLOWED_FIELDS and value not in (None, ""):
                    updates[key] = value
        return updates

    def _apply_updates(self, config: dict, updates: dict) -> dict:
        result = json.loads(json.dumps(config))
        result.setdefault("campaign", {})
        result.setdefault("assets", {})
        result.setdefault("links", {})
        result.setdefault("meta", {})
        result.setdefault("approval", {})

        link = updates.get("landing_url") or updates.get("link")
        if link:
            result["links"]["landing_url"] = link
            result["campaign"]["link"] = link
        if updates.get("image_url"):
            result["assets"]["image_url"] = updates["image_url"]
            result["campaign"]["image_url"] = updates["image_url"]
        if updates.get("privacy_url"):
            result["links"]["privacy_url"] = updates["privacy_url"]
            result["campaign"]["privacy_url"] = updates["privacy_url"]
        if updates.get("whatsapp_number"):
            result["links"]["whatsapp_number"] = updates["whatsapp_number"]
        if updates.get("approver"):
            result["approval"]["approver"] = updates["approver"]
            result["approval"]["status"] = updates.get("approval_status") or result["approval"].get("status") or "pendiente"
        if updates.get("status"):
            result["campaign"]["status"] = str(updates["status"]).upper()

        budget = result["campaign"].setdefault("budget", {})
        if not isinstance(budget, dict):
            budget = {"daily": budget}
            result["campaign"]["budget"] = budget
        if updates.get("daily_budget") is not None:
            budget["daily"] = updates["daily_budget"]
        if updates.get("total_budget") is not None:
            budget["total"] = updates["total_budget"]
        if updates.get("days") is not None:
            result["campaign"]["days"] = updates["days"]

        for key in ("meta_ad_account_id", "meta_page_id", "meta_app_id", "form_id", "campaign_id", "adset_id", "creative_id", "ad_id"):
            if updates.get(key):
                result["meta"][key] = updates[key]

        if updates.get("notes"):
            result.setdefault("notes", [])
            notes = updates["notes"] if isinstance(updates["notes"], list) else [updates["notes"]]
            result["notes"].extend(str(note) for note in notes)
        return result
