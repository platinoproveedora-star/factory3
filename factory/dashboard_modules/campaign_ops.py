"""Reusable Streamlit branch for campaign operations dashboards.

Import this module from any Streamlit dashboard and call `render_campaign_ops`.
It intentionally delegates backend work to existing Factory skills.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Callable


RunSkill = Callable[[str, dict, str], dict]


def render_campaign_ops(
    run_skill: RunSkill,
    company_id: str,
    campaign_slug: str = "first_campaign",
    default_bucket: str = "campaign-assets",
) -> None:
    """Render a generic Campaign Ops branch.

    Parameters
    ----------
    run_skill:
        Dashboard helper that executes Factory skills.
    company_id:
        Company identifier, e.g. EMP_CAMP_RSTATE.
    campaign_slug:
        Logical campaign folder/key.
    default_bucket:
        Supabase Storage bucket used for uploads.
    """

    import pandas as pd
    import streamlit as st

    st.title("Campaign Ops")
    st.caption(f"{company_id} / {campaign_slug}")

    tab_overview, tab_campaign, tab_uploads, tab_preflight, tab_leads, tab_results, tab_settings = st.tabs(
        ["Overview", "Campaign", "Uploads", "Preflight", "Leads", "Results", "Settings"]
    )

    state_key = f"campaign_ops_{company_id}_{campaign_slug}"
    st.session_state.setdefault(state_key, {})
    state = st.session_state[state_key]
    _hydrate_state_from_campaign_file(state, company_id, campaign_slug)

    with tab_overview:
        st.subheader("Readiness")
        preflight = _run_preflight(run_skill, company_id, campaign_slug, state)
        if preflight.get("ok"):
            data = preflight.get("data", {})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ready", "Yes" if data.get("ready_to_launch") else "No")
            c2.metric("Risk", data.get("risk_level", "n/a"), data.get("risk_score", 0))
            c3.metric("Blockers", data.get("summary", {}).get("blockers", 0))
            c4.metric("Warnings", data.get("summary", {}).get("warnings", 0))
            blockers = data.get("blockers", [])
            if blockers:
                st.warning("Blockers pendientes")
                st.dataframe(pd.DataFrame(blockers), use_container_width=True, hide_index=True)
            else:
                st.success("Sin blockers de preflight")
        else:
            st.error(preflight.get("error", "No se pudo correr preflight"))

    with tab_campaign:
        st.subheader("Campaign Plan")
        if st.button("Run campaign dry run", key=f"{state_key}_campaign_run"):
            state["campaign_run"] = _run_campaign(run_skill, company_id, campaign_slug, state)
        result = state.get("campaign_run")
        if result:
            if result.get("ok"):
                data = result.get("data", {})
                st.json(
                    {
                        "campaign": (data.get("company_context") or {}).get("campaign"),
                        "planned_payloads": data.get("planned_payloads"),
                        "execution": data.get("execution"),
                    },
                    expanded=False,
                )
            else:
                st.error(result.get("error", "Campaign run failed"))
        else:
            st.info("Run a dry run to generate campaign payloads.")

    with tab_uploads:
        st.subheader("Uploads")
        bucket = st.text_input("Bucket", value=state.get("bucket", default_bucket), key=f"{state_key}_bucket")
        folder = st.text_input(
            "Folder",
            value=state.get("folder", f"{company_id}/{campaign_slug}"),
            key=f"{state_key}_folder",
        )
        uploaded = st.file_uploader(
            "Upload campaign images",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"{state_key}_uploader",
        )
        if uploaded:
            st.caption(f"{len(uploaded)} file(s) selected")
            for file in uploaded:
                st.write(file.name)
        if st.button("Upload to storage", key=f"{state_key}_upload_btn", disabled=not uploaded):
            urls = []
            for file in uploaded or []:
                content = file.getvalue()
                path = f"{folder.rstrip('/')}/{_safe_filename(file.name)}"
                result = run_skill(
                    "supabase_storage_upload",
                    {
                        "bucket": bucket,
                        "path": path,
                        "content_b64": base64.b64encode(content).decode("ascii"),
                        "content_type": file.type or "application/octet-stream",
                        "dry_run": False,
                    },
                    "internos",
                )
                if result.get("ok"):
                    data = result.get("data", {})
                    url = data.get("public_url") or data.get("url")
                    urls.append(url)
                    st.success(f"Uploaded: {file.name}")
                else:
                    st.error(f"{file.name}: {result.get('error', 'upload failed')}")
            state["asset_urls"] = [url for url in urls if url]
        if state.get("asset_urls"):
            st.markdown("Asset URLs")
            st.json(state["asset_urls"], expanded=False)
            if st.button("Use first image as image_url", key=f"{state_key}_use_first"):
                state["image_url"] = state["asset_urls"][0]
                st.success("image_url updated in dashboard state")

    with tab_preflight:
        st.subheader("Preflight")
        privacy_url = st.text_input("Privacy URL", value=state.get("privacy_url", ""), key=f"{state_key}_privacy")
        image_url = st.text_input("Image URL", value=state.get("image_url", ""), key=f"{state_key}_image")
        link = st.text_input("Landing / WhatsApp / Post URL", value=state.get("link", ""), key=f"{state_key}_link")
        approver = st.text_input("Approver", value=state.get("approver", "pendiente"), key=f"{state_key}_approver")
        state.update({"privacy_url": privacy_url, "image_url": image_url, "link": link, "approver": approver})
        if st.button("Run preflight", key=f"{state_key}_preflight_btn"):
            state["preflight"] = _run_preflight(run_skill, company_id, campaign_slug, state)
        result = state.get("preflight")
        if result:
            if result.get("ok"):
                data = result.get("data", {})
                st.metric("Ready to launch", "Yes" if data.get("ready_to_launch") else "No")
                st.json(data, expanded=False)
            else:
                st.error(result.get("error", "Preflight failed"))

    with tab_leads:
        st.subheader("Leads")
        if st.button("Load sales report", key=f"{state_key}_sales_report"):
            state["sales_report"] = run_skill(
                "vertical_sales/sales_report",
                {"empresa_id": company_id, "dry_run": False},
                "internos",
            )
        result = state.get("sales_report")
        if result:
            if result.get("ok"):
                st.json(result.get("data", {}), expanded=False)
            else:
                st.error(result.get("error", "Sales report failed"))
        else:
            st.info("Load sales report once Supabase sales tables are configured.")

    with tab_results:
        st.subheader("Ad Results")
        level = st.selectbox("Level", ["campaign", "adset", "ad"], key=f"{state_key}_level")
        object_id = st.text_input("Meta object id", value=state.get("meta_object_id", ""), key=f"{state_key}_object")
        if st.button("Get Meta insights", key=f"{state_key}_insights", disabled=not object_id):
            state["insights"] = run_skill(
                "vertical_meta_ads/meta_ads_get_insights",
                {"level": level, "object_id": object_id, "dry_run": False},
                "internos",
            )
        result = state.get("insights")
        if result:
            if result.get("ok"):
                st.json(result.get("data", {}), expanded=False)
            else:
                st.error(result.get("error", "Insights failed"))
        else:
            st.info("Results appear after the campaign exists in Meta.")

    with tab_settings:
        st.subheader("Company Config")
        result = run_skill(
            "vertical_companies/company_config_loader",
            {"company_id": company_id},
            "internos",
        )
        if result.get("ok"):
            st.json(result.get("data", {}).get("config", {}), expanded=False)
        else:
            st.error(result.get("error", "Could not load company config"))
        st.caption(f"Last rendered: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")


def _run_campaign(run_skill: RunSkill, company_id: str, campaign_slug: str, state: dict) -> dict:
    return run_skill(
        "vertical_ads/ads_campaign_run",
        {
            "company_id": company_id,
            "dry_run": True,
            "execute": False,
            "privacy_url": state.get("privacy_url"),
            "image_url": state.get("image_url"),
            "link": state.get("link"),
            "approver": state.get("approver") or "pendiente",
            "message": state.get("message"),
            "title": state.get("title"),
            "description": state.get("description"),
            "brief": state.get("brief") or {},
            "campaign_slug": campaign_slug,
        },
        "internos",
    )


def _run_preflight(run_skill: RunSkill, company_id: str, campaign_slug: str, state: dict) -> dict:
    return run_skill(
        "vertical_ads/ads_campaign_preflight_check",
        {
            "company_id": company_id,
            "dry_run": True,
            "execute": False,
            "privacy_url": state.get("privacy_url"),
            "image_url": state.get("image_url"),
            "link": state.get("link"),
            "approver": state.get("approver") or "pendiente",
            "message": state.get("message"),
            "title": state.get("title"),
            "description": state.get("description"),
            "brief": state.get("brief") or {},
            "campaign_slug": campaign_slug,
        },
        "internos",
    )


def _safe_filename(name: str) -> str:
    keep = []
    for ch in name.strip().replace(" ", "-").lower():
        if ch.isalnum() or ch in {".", "-", "_"}:
            keep.append(ch)
    return "".join(keep) or "asset"


def _hydrate_state_from_campaign_file(state: dict, company_id: str, campaign_slug: str) -> None:
    if state.get("_campaign_file_loaded"):
        return
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "companies" / company_id / f"{campaign_slug}.json",
        root / "companies" / company_id / "campaign.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            state.setdefault("brief", payload.get("brief") or {})
            state.setdefault("message", payload.get("message") or "")
            state.setdefault("title", payload.get("title") or "")
            state.setdefault("description", payload.get("description") or "")
            state.setdefault("privacy_url", payload.get("privacy_url") or "")
            state.setdefault("image_url", payload.get("image_url") or "")
            state.setdefault("link", payload.get("link") or "")
            state.setdefault("approver", payload.get("approver") or "pendiente")
            state["_campaign_file_loaded"] = str(path)
            return
    state["_campaign_file_loaded"] = "missing"
