from __future__ import annotations

import re
from typing import Any

from factory.engine import SupabaseClient

from gptads_common import clean_text, slug

_VALID_SCHEMA = re.compile(r"^[a-z][a-z0-9_]*$")


def tenant_context(context: dict) -> dict:
    schema = clean_text(context.get("schema") or context.get("supabase_schema") or context.get("db_schema"))
    if not schema or not _VALID_SCHEMA.match(schema):
        return {"ok": False, "error": "schema requerido y valido"}
    company_id = clean_text(context.get("company_id") or context.get("empresa_id"))
    if not company_id:
        return {"ok": False, "error": "company_id requerido"}
    ctx = dict(context)
    ctx["schema"] = schema
    ctx["company_id"] = company_id
    ctx["empresa_id"] = company_id
    ctx.setdefault("project_code", clean_text(context.get("project_code")) or "PROY-001")
    ctx.setdefault("module_code", clean_text(context.get("module_code")) or "gptads4all")
    return {"ok": True, "data": ctx}


def product_key_from_name(name: str) -> str:
    return f"prod_{slug(name)[:48]}"


def product_payload(ctx: dict, context: dict) -> dict:
    name = clean_text(context.get("product_name"))
    product_key = clean_text(context.get("product_key")) or product_key_from_name(name)
    return {
        "empresa_id": ctx["company_id"],
        "company_id": ctx["company_id"],
        "project_code": ctx.get("project_code"),
        "module_code": ctx.get("module_code"),
        "product_key": product_key,
        "product_name": name,
        "description": clean_text(context.get("description") or context.get("base_brief")) or None,
        "base_brief": clean_text(context.get("base_brief") or context.get("description")) or None,
        "category": clean_text(context.get("category")) or None,
        "status": clean_text(context.get("status")) or "active",
        "market": context.get("market") if isinstance(context.get("market"), dict) else None,
        "metadata": context.get("metadata") if isinstance(context.get("metadata"), dict) else {},
    }


def save_product(ctx: dict, context: dict) -> dict:
    payload = product_payload(ctx, context)
    if not payload["product_name"]:
        return {"ok": False, "error": "product_name requerido"}
    if context.get("dry_run", True):
        return {"ok": True, "message": "dry_run", "data": {"product": payload}}
    db = SupabaseClient(ctx)
    res = db.rest_upsert("products", payload, "empresa_id,product_key")
    if not res.get("ok") and any(col in str(res.get("error") or "") for col in ["company_id", "base_brief", "metadata", "status", "project_code", "module_code"]):
        legacy = {
            key: payload.get(key)
            for key in (
                "empresa_id",
                "product_key",
                "product_name",
                "description",
                "category",
                "price_range",
                "url",
                "market",
                "value_props",
                "tone",
            )
            if key in payload
        }
        res = db.rest_upsert("products", legacy, "empresa_id,product_key")
    if not res.get("ok"):
        return res
    rows = res.get("data") or []
    return {"ok": True, "data": {"product": rows[0] if rows else payload}}


def save_brief(ctx: dict, context: dict) -> dict:
    product = context.get("product") if isinstance(context.get("product"), dict) else {}
    product_key = clean_text(context.get("product_key") or product.get("product_key"))
    product_id = clean_text(context.get("product_id") or product.get("id"))
    raw_brief = clean_text(context.get("raw_brief") or context.get("base_brief") or context.get("description"))
    if not product_key:
        return {"ok": False, "error": "product_key requerido"}
    if not raw_brief:
        return {"ok": False, "error": "raw_brief requerido"}
    analysis = context.get("brief_analysis") if isinstance(context.get("brief_analysis"), dict) else {}
    payload = {
        "empresa_id": ctx["company_id"],
        "company_id": ctx["company_id"],
        "project_code": ctx.get("project_code"),
        "module_code": ctx.get("module_code"),
        "product_id": product_id or None,
        "product_key": product_key,
        "raw_brief": raw_brief,
        "brief_analysis": analysis or None,
        "optimized_description": clean_text(context.get("optimized_description") or analysis.get("optimized_description")) or None,
        "objective_recommended": clean_text(context.get("objective_recommended") or analysis.get("objective_recommended")) or None,
        "channel_recommended": clean_text(context.get("channel_recommended") or analysis.get("channel_recommended")) or None,
        "quality_score": context.get("quality_score") or analysis.get("quality_score"),
        "output_language": clean_text(context.get("output_language") or analysis.get("output_language")) or None,
        "creative_angles": context.get("creative_angles") if isinstance(context.get("creative_angles"), list) else analysis.get("creative_angles"),
        "missing_fields": context.get("missing_fields") if isinstance(context.get("missing_fields"), list) else analysis.get("missing_fields"),
        "status": clean_text(context.get("status")) or "active",
    }
    if context.get("dry_run", True):
        return {"ok": True, "message": "dry_run", "data": {"brief": payload}}
    res = SupabaseClient(ctx).rest_insert("briefs", payload)
    if not res.get("ok"):
        return res
    rows = res.get("data") or []
    return {"ok": True, "data": {"brief": rows[0] if rows else payload}}


def list_products(ctx: dict, context: dict) -> dict:
    limit = int(context.get("limit") or 100)
    if context.get("dry_run", True):
        return {"ok": True, "message": "dry_run", "data": {"products": [], "limit": limit}}
    res = SupabaseClient(ctx).rest_select(
        "products",
        filters={"empresa_id": f"eq.{ctx['company_id']}"},
        select="id,folio,empresa_id,company_id,project_code,module_code,product_key,product_name,base_brief,description,category,status,market,created_at,updated_at",
        order="updated_at.desc",
        limit=limit,
    )
    if not res.get("ok") and any(col in str(res.get("error") or "") for col in ["company_id", "base_brief", "status", "project_code", "module_code"]):
        res = SupabaseClient(ctx).rest_select(
            "products",
            filters={"empresa_id": f"eq.{ctx['company_id']}"},
            select="id,folio,empresa_id,product_key,product_name,description,category,market,created_at,updated_at",
            order="updated_at.desc",
            limit=limit,
        )
    if not res.get("ok"):
        return res
    return {"ok": True, "data": {"products": res.get("data") or []}}


def list_briefs(ctx: dict, context: dict) -> dict:
    filters: dict[str, Any] = {"empresa_id": f"eq.{ctx['company_id']}"}
    product_key = clean_text(context.get("product_key"))
    if product_key:
        filters["product_key"] = f"eq.{product_key}"
    limit = int(context.get("limit") or 50)
    if context.get("dry_run", True):
        return {"ok": True, "message": "dry_run", "data": {"briefs": [], "limit": limit}}
    res = SupabaseClient(ctx).rest_select(
        "briefs",
        filters=filters,
        select="id,folio,empresa_id,company_id,product_id,product_key,raw_brief,brief_analysis,optimized_description,objective_recommended,channel_recommended,quality_score,output_language,creative_angles,missing_fields,status,created_at,updated_at",
        order="created_at.desc",
        limit=limit,
    )
    if not res.get("ok"):
        return res
    return {"ok": True, "data": {"briefs": res.get("data") or []}}


def campaign_history(ctx: dict, context: dict) -> dict:
    filters: dict[str, Any] = {"empresa_id": f"eq.{ctx['company_id']}"}
    product_key = clean_text(context.get("product_key"))
    if product_key:
        filters["product_key"] = f"eq.{product_key}"
    limit = int(context.get("limit") or 25)
    if context.get("dry_run", True):
        return {"ok": True, "message": "dry_run", "data": {"campaigns": [], "used_angles": []}}
    res = SupabaseClient(ctx).rest_select(
        "campaigns",
        filters=filters,
        select="id,folio,empresa_id,company_id,product_id,brief_id,product_key,campaign_key,campaign_name,objective,status,creative_angles_used,daily_budget_amount,currency,created_at,updated_at",
        order="created_at.desc",
        limit=limit,
    )
    if not res.get("ok"):
        return res
    campaigns = res.get("data") or []
    used = []
    for row in campaigns:
        angles = row.get("creative_angles_used")
        if isinstance(angles, list):
            used.extend(clean_text(item) for item in angles if clean_text(item))
    return {"ok": True, "data": {"campaigns": campaigns, "used_angles": sorted(set(used))}}
