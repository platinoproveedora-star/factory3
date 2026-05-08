"""Broadcast a grupos/contactos de WhatsApp. Backends: twilio, meta, playwright, dry_run."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from factory.engine import SupabaseClient


class WhatsappGroupBroadcasterService:

    def ejecutar(self, context: dict) -> dict:
        texto:      str  = context.get("texto") or ""
        destinos:   list = context.get("destinos") or []   # lista de numeros o group_ids
        backend:    str  = context.get("backend") or os.getenv("WA_BACKEND", "dry_run")
        guardar:    bool = context.get("guardar", True)
        vacante_id: str  = context.get("vacante_id") or ""
        empresa_id: str  = context.get("empresa_id") or ""

        if not texto:
            return {"ok": False, "error": "texto es requerido"}
        if not destinos:
            return {"ok": False, "error": "destinos es requerido (lista de numeros o group_ids)"}

        resultados = []
        for destino in destinos:
            if backend == "twilio":
                r = self._enviar_twilio(texto, destino, context)
            elif backend == "meta":
                r = self._enviar_meta(texto, destino, context)
            elif backend == "playwright":
                r = self._enviar_playwright(texto, destino, context)
            else:
                r = self._dry_run(texto, destino)
            resultados.append(r)

        if guardar:
            self._guardar(resultados, texto, vacante_id, empresa_id, backend)

        enviados = sum(1 for r in resultados if r.get("enviado"))
        return {
            "ok": True,
            "data": {
                "total":      len(resultados),
                "enviados":   enviados,
                "fallidos":   len(resultados) - enviados,
                "backend":    backend,
                "resultados": resultados,
            },
        }

    # ── Backends ───────────────────────────────────────────────────────────────

    def _dry_run(self, texto: str, destino: str) -> dict:
        return {
            "destino":   destino,
            "enviado":   False,
            "dry_run":   True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mensaje":   f"dry_run — configura WA_BACKEND=twilio|meta|playwright para enviar realmente.",
        }

    def _enviar_twilio(self, texto: str, destino: str, context: dict) -> dict:
        sid   = context.get("twilio_sid")   or os.getenv("TWILIO_SID", "")
        token = context.get("twilio_token") or os.getenv("TWILIO_AUTH_TOKEN", "")
        from_ = context.get("twilio_from")  or os.getenv("TWILIO_WA_FROM", "")

        if not sid or not token or not from_:
            return {"destino": destino, "enviado": False, "error": "Faltan TWILIO_SID, TWILIO_AUTH_TOKEN o TWILIO_WA_FROM"}

        try:
            import httpx
            resp = httpx.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                auth=(sid, token),
                data={"From": f"whatsapp:{from_}", "To": f"whatsapp:{destino}", "Body": texto},
                timeout=15,
            )
            ok = resp.status_code in (200, 201)
            return {"destino": destino, "enviado": ok, "status": resp.status_code,
                    "error": resp.text if not ok else None}
        except Exception as e:
            return {"destino": destino, "enviado": False, "error": str(e)}

    def _enviar_meta(self, texto: str, destino: str, context: dict) -> dict:
        token    = context.get("wa_token")    or os.getenv("WA_META_TOKEN", "")
        phone_id = context.get("wa_phone_id") or os.getenv("WA_PHONE_ID", "")

        if not token or not phone_id:
            return {"destino": destino, "enviado": False, "error": "Faltan WA_META_TOKEN o WA_PHONE_ID"}

        try:
            import httpx
            resp = httpx.post(
                f"https://graph.facebook.com/v19.0/{phone_id}/messages",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"messaging_product": "whatsapp", "to": destino,
                      "type": "text", "text": {"body": texto}},
                timeout=15,
            )
            ok = resp.status_code in (200, 201)
            return {"destino": destino, "enviado": ok, "status": resp.status_code,
                    "error": resp.json() if not ok else None}
        except Exception as e:
            return {"destino": destino, "enviado": False, "error": str(e)}

    def _enviar_playwright(self, texto: str, destino: str, context: dict) -> dict:
        # Placeholder — Playwright WA Web requiere sesion activa y es fragil
        return {"destino": destino, "enviado": False,
                "error": "Backend playwright para WA no implementado aun — usa twilio o meta"}

    # ── Persistencia ───────────────────────────────────────────────────────────

    def _guardar(self, resultados: list, texto: str, vacante_id: str, empresa_id: str, backend: str) -> None:
        db = SupabaseClient({})
        for r in resultados:
            db.rest_insert("whatsapp_broadcasts", {
                "destino":    r.get("destino"),
                "texto":      texto[:500],
                "enviado":    r.get("enviado", False),
                "backend":    backend,
                "vacante_id": vacante_id,
                "empresa_id": empresa_id,
                "fecha":      datetime.now(timezone.utc).isoformat(),
                "error":      str(r.get("error") or ""),
            })
