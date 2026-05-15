from __future__ import annotations

from pathlib import Path


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    ext_root = root.parent / "externos"
    ext_root.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(
        internal_root=root,
        external_root=ext_root,
        extra_roots={"meta": root.parent / "meta", "eval": root.parent / "eval"},
    )
    return SkillRunner(loader)


def _run(name: str, ctx: dict) -> dict:
    return _runner().run(name, ctx, source="internos")


class CampaignLaunchPausedService:
    """Safe wrapper that only prepares/creates campaigns in PAUSED."""

    def ejecutar(self, context: dict) -> dict:
        form_id = str(context.get("form_id") or "").strip()
        execute = bool(context.get("execute", False))
        require_ready = bool(context.get("require_ready", True))
        if not form_id:
            return {"ok": False, "error": "form_id requerido. Crea primero el Lead Form."}

        preflight = _run("vertical_ads/ads_campaign_preflight_check", {
            **context,
            "dry_run": True,
            "execute": False,
        })
        if not preflight.get("ok"):
            return preflight
        preflight_data = preflight.get("data") or {}
        if require_ready and not preflight_data.get("ready_to_launch"):
            return {
                "ok": False,
                "error": "preflight no esta ready_to_launch",
                "data": {"preflight": preflight_data},
            }

        plan = _run("vertical_ads/ads_campaign_run", {
            **context,
            "dry_run": True,
            "execute": False,
            "status": "PAUSED",
        })
        if not plan.get("ok"):
            return plan

        planned_payloads = (plan.get("data") or {}).get("planned_payloads") or {}
        lead_campaign = {
            **(planned_payloads.get("lead_campaign") or {}),
            "form_id": form_id,
            "status": "PAUSED",
            "dry_run": not execute,
        }
        for key in ("access_token", "ad_account_id", "page_id", "image_url", "link", "message", "title", "description", "daily_budget", "days", "targeting"):
            if context.get(key) not in (None, ""):
                lead_campaign[key] = context[key]

        if not execute:
            return {
                "ok": True,
                "data": {
                    "dry_run": True,
                    "status": "PAUSED",
                    "preflight": preflight_data,
                    "payload": lead_campaign,
                    "next_action": "Revisar payload; luego repetir con execute=true para crear en Meta en PAUSED.",
                },
            }

        launch = _run("vertical_meta_ads/meta_ads_lead_campaign_flow", lead_campaign)
        return {
            "ok": launch.get("ok", False),
            "error": launch.get("error"),
            "data": {
                "status": "PAUSED",
                "preflight": preflight_data,
                "payload": lead_campaign,
                "launch_result": launch.get("data"),
            },
        }
