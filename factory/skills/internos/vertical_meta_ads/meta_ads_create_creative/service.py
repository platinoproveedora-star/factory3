"""Crea un creativo de anuncio con imagen/video, copy, enlace y call-to-action."""
from __future__ import annotations
import json, os, urllib.request, urllib.parse

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"
_CTA_TYPES = {
    "LEARN_MORE", "SHOP_NOW", "SIGN_UP", "CONTACT_US", "DOWNLOAD",
    "GET_OFFER", "BOOK_TRAVEL", "WATCH_MORE", "NO_BUTTON", "SUBSCRIBE",
    "SEND_MESSAGE", "CALL_NOW", "GET_DIRECTIONS",
}


class MetaAdsCreateCreativeService:

    def ejecutar(self, context: dict) -> dict:
        token = context.get("access_token") or os.getenv("META_ACCESS_TOKEN", "")
        ad_account_id = context.get("ad_account_id") or os.getenv("META_AD_ACCOUNT_ID", "")
        page_id = context.get("page_id") or os.getenv("META_PAGE_ID", "")
        nombre = (context.get("nombre") or context.get("name") or "").strip()
        mensaje = (context.get("mensaje") or context.get("message") or "").strip()
        link = (context.get("link") or "").strip()

        if not token:
            return {"ok": False, "error": "access_token requerido"}
        if not ad_account_id:
            return {"ok": False, "error": "ad_account_id requerido"}
        if not page_id:
            return {"ok": False, "error": "page_id requerido"}
        if not nombre:
            return {"ok": False, "error": "nombre requerido"}
        if not link:
            return {"ok": False, "error": "link requerido (URL de destino)"}

        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        cta_type = (context.get("cta_type") or "LEARN_MORE").upper()
        image_url = context.get("image_url", "")
        titulo = context.get("titulo") or context.get("title") or ""

        link_data: dict = {"link": link}
        if mensaje:
            link_data["message"] = mensaje
        if titulo:
            link_data["name"] = titulo
        if image_url:
            link_data["picture"] = image_url
        if cta_type and cta_type in _CTA_TYPES:
            link_data["call_to_action"] = {"type": cta_type, "value": {"link": link}}

        story_spec = {"page_id": page_id, "link_data": link_data}

        if context.get("dry_run", True):
            return {"ok": True, "data": {"dry_run": True, "nombre": nombre, "link": link, "cta_type": cta_type}}

        try:
            payload = {
                "name":               nombre,
                "object_story_spec":  json.dumps(story_spec),
            }
            data = self._post(f"{ad_account_id}/adcreatives", payload, token)
            if "error" in data:
                err = data["error"]
                return {"ok": False, "error": err.get("message", str(err))}

            return {"ok": True, "data": {"creative_id": data.get("id"), "nombre": nombre}}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _post(self, path: str, payload: dict, token: str) -> dict:
        payload["access_token"] = token
        data = urllib.parse.urlencode(payload).encode()
        url = f"https://graph.facebook.com/{_VERSION}/{path}"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": _UA}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
