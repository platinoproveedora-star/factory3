"""Service for rh_qr_entry — genera QR con link directo al bot de captura."""

from __future__ import annotations
import base64
import io
import urllib.parse


class RhQrEntryService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}

        bot_url = context["bot_url"]
        vacante_id = context.get("vacante_id", "")
        empresa_id = context.get("empresa_id", "")
        canal = context.get("canal", "telegram")

        params: dict = {}
        if vacante_id:
            params["vacante_id"] = vacante_id
        if empresa_id:
            params["empresa_id"] = empresa_id

        if params:
            link = f"{bot_url}?{urllib.parse.urlencode(params)}"
        else:
            link = bot_url

        resultado: dict = {
            "ok": True,
            "data": {
                "link": link,
                "canal": canal,
                "vacante_id": vacante_id,
                "empresa_id": empresa_id,
                "qr_generado": False,
            },
        }

        qr_b64 = self._generar_qr(link)
        if qr_b64:
            resultado["data"]["qr_b64"] = qr_b64
            resultado["data"]["qr_generado"] = True

        return resultado

    def _generar_qr(self, link: str) -> str | None:
        try:
            import qrcode  # type: ignore
            img = qrcode.make(link)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            return None

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not context.get("bot_url"):
            return False, "bot_url es requerido (ej: https://t.me/mi_bot)"
        return True, None
