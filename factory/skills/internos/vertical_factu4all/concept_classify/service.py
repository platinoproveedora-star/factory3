from __future__ import annotations

from pathlib import Path

from factory.engine import SupabaseClient

_SCHEMA = "factu4all"


def _runner():
    from factory.engine import SkillLoader, SkillRunner

    root = Path(__file__).resolve().parents[2]
    return SkillRunner(SkillLoader(internal_root=root))


class ConceptClassifyService:
    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id_requerido"}

        product_id = str(context.get("product_id") or "").strip()
        source_product_key = str(context.get("source_product_key") or "").strip()

        manual = self._manual_override(context, company_id, product_id, source_product_key)
        if manual:
            return {"ok": True, "data": manual}

        res = _runner().run("vertical_sat/sat_prodserv_classify", {
            "uso_cfdi": context.get("uso_cfdi"),
            "clave_prod_serv": context.get("clave_prod_serv"),
        })
        if not res.get("ok"):
            return res
        return {"ok": True, "data": res["data"]}

    def _manual_override(self, context: dict, company_id: str, product_id: str, source_product_key: str) -> dict | None:
        if not product_id and not source_product_key:
            return None
        db = SupabaseClient({**context, "schema": _SCHEMA})
        filters = {"company_id": f"eq.{company_id}"}
        if product_id:
            filters["id"] = f"eq.{product_id}"
        else:
            filters["source_product_key"] = f"eq.{source_product_key}"
        res = db.rest_select("products", filters=filters, select="classification_group,classification_source", limit=1)
        if not res.get("ok") or not res.get("data"):
            return None
        product = res["data"][0]
        if product.get("classification_source") == "manual" and product.get("classification_group"):
            return {"classification_group": product["classification_group"], "source": "manual", "signal": product_id or source_product_key}
        return None
