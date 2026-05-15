"""Checklist QA completo antes de lanzar una campaña."""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

_SEMAFORO = {"pass": "PASS", "fail": "FAIL", "warn": "WARN", "skip": "SKIP"}


class QAPreflightService:

    def ejecutar(self, context: dict) -> dict:
        company_id  = (context.get("company_id") or "").strip()
        campaign_id = (context.get("campaign_id") or "").strip()

        if not company_id:
            return {"ok": False, "error": "company_id requerido"}

        checks: list[dict] = []

        skip_urls = bool(context.get("skip_url_checks", False))

        # 1. Landing visible
        landing_url = context.get("landing_url", "")
        if skip_urls and not landing_url:
            checks.append(self._item("landing_url", "skip", "URL check omitido (skip_url_checks=True)"))
        else:
            self._check_url(checks, "landing_url", landing_url,
                            "Landing page accesible desde internet")

        # 2. WhatsApp link
        whatsapp = context.get("whatsapp_link", "")
        if skip_urls and not whatsapp:
            checks.append(self._item("whatsapp_link", "skip", "URL check omitido"))
        else:
            self._check_whatsapp(checks, whatsapp)

        # 3. Privacy URL
        privacy_url = context.get("privacy_url", "")
        if skip_urls and not privacy_url:
            checks.append(self._item("privacy_url", "skip", "URL check omitido"))
        else:
            self._check_url(checks, "privacy_url", privacy_url,
                            "URL de Política de Privacidad accesible")

        # 4. Imagen de campaña
        image_url = context.get("image_url", "")
        if skip_urls and not image_url:
            checks.append(self._item("image_url", "skip", "URL check omitido"))
        else:
            self._check_url(checks, "image_url", image_url,
                            "Imagen de campaña accesible (URL pública)")

        # 5. Lead form ID
        self._check_field(checks, "lead_form_id",
                          context.get("lead_form_id"),
                          "ID del formulario de leads configurado")

        # 6. Presupuesto diario
        self._check_budget(checks, context.get("daily_budget"))

        # 7. Copy (mensaje del anuncio)
        self._check_copy(checks, context.get("ad_copy", ""))

        # 8. Approver
        self._check_field(checks, "approver",
                          context.get("approver"),
                          "Responsable aprobador de la campaña asignado")

        # 9. Pixel/tracking configurado
        self._check_field(checks, "pixel_id",
                          context.get("pixel_id"),
                          "Pixel Meta (CAPI o browser) configurado")

        # 10. Meta token válido (no expirado)
        self._check_meta_token(checks, context)

        # 11. Campaign en modo PAUSED al crear
        campaign_status = (context.get("campaign_status") or "PAUSED").upper()
        if campaign_status == "PAUSED":
            checks.append(self._item("campaign_status", "pass",
                                     "Campaña inicialmente en PAUSED — seguro"))
        else:
            checks.append(self._item("campaign_status", "fail",
                                     f"campaign_status={campaign_status}. Debe ser PAUSED antes de lanzar"))

        passed  = [c for c in checks if c["status"] == "pass"]
        failed  = [c for c in checks if c["status"] == "fail"]
        warned  = [c for c in checks if c["status"] == "warn"]
        skipped = [c for c in checks if c["status"] == "skip"]

        listo = len(failed) == 0
        return {
            "ok": listo,
            "message": (
                f"Preflight OK — {len(passed)}/{len(checks)} checks pasados"
                if listo
                else f"Preflight BLOQUEADO — {len(failed)} checks fallidos"
            ),
            "data": {
                "company_id":  company_id,
                "campaign_id": campaign_id,
                "timestamp":   datetime.now(timezone.utc).isoformat(),
                "listo_para_lanzar": listo,
                "resumen": {
                    "pass":  len(passed),
                    "fail":  len(failed),
                    "warn":  len(warned),
                    "skip":  len(skipped),
                    "total": len(checks),
                },
                "checks_fallidos": [c["nombre"] for c in failed],
                "checks": checks,
            },
        }

    # ── CHECKS INDIVIDUALES ──────────────────────────────────────────────────

    def _check_url(self, checks: list, nombre: str, url: str, desc: str) -> None:
        if not url:
            checks.append(self._item(nombre, "fail", f"{desc} — URL no configurada"))
            return
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "FactoryQA/0.1"},
                method="HEAD",
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                code = r.status
            if code < 400:
                checks.append(self._item(nombre, "pass", f"{desc} — HTTP {code}"))
            else:
                checks.append(self._item(nombre, "fail", f"{desc} — HTTP {code}"))
        except urllib.error.HTTPError as e:
            if e.code < 400:
                checks.append(self._item(nombre, "pass", f"{desc} — HTTP {e.code}"))
            else:
                checks.append(self._item(nombre, "fail", f"{desc} — HTTP {e.code}: {e.reason}"))
        except Exception as exc:
            checks.append(self._item(nombre, "fail", f"{desc} — {exc}"))

    def _check_whatsapp(self, checks: list, link: str) -> None:
        if not link:
            checks.append(self._item("whatsapp_link", "fail",
                                     "Link de WhatsApp no configurado"))
            return
        ok = link.startswith("https://wa.me/") or link.startswith("https://api.whatsapp.com/")
        if ok:
            checks.append(self._item("whatsapp_link", "pass",
                                     f"Link WhatsApp válido: {link}"))
        else:
            checks.append(self._item("whatsapp_link", "warn",
                                     f"Link no sigue formato wa.me o api.whatsapp.com: {link}"))

    def _check_budget(self, checks: list, budget) -> None:
        if budget is None or budget == "":
            checks.append(self._item("daily_budget", "fail",
                                     "Presupuesto diario no configurado"))
            return
        try:
            amt = float(budget)
        except (ValueError, TypeError):
            checks.append(self._item("daily_budget", "fail",
                                     f"Presupuesto no es número: {budget}"))
            return
        if amt <= 0:
            checks.append(self._item("daily_budget", "fail",
                                     f"Presupuesto debe ser > 0 (actual: {amt})"))
        elif amt < 50:
            checks.append(self._item("daily_budget", "warn",
                                     f"Presupuesto bajo (${amt}/día) — Meta puede limitar alcance"))
        else:
            checks.append(self._item("daily_budget", "pass",
                                     f"Presupuesto configurado: ${amt}/día"))

    def _check_copy(self, checks: list, copy_text: str) -> None:
        if not copy_text or not copy_text.strip():
            checks.append(self._item("ad_copy", "fail",
                                     "Copy del anuncio vacío"))
            return
        words = len(copy_text.split())
        if words < 5:
            checks.append(self._item("ad_copy", "warn",
                                     f"Copy muy corto ({words} palabras)"))
        elif words > 200:
            checks.append(self._item("ad_copy", "warn",
                                     f"Copy muy largo ({words} palabras) — Meta puede truncar"))
        else:
            checks.append(self._item("ad_copy", "pass",
                                     f"Copy configurado ({words} palabras)"))

    def _check_field(self, checks: list, nombre: str, value, desc: str) -> None:
        if value and str(value).strip():
            checks.append(self._item(nombre, "pass", f"{desc} — {value}"))
        else:
            checks.append(self._item(nombre, "fail", f"{desc} — no configurado"))

    def _check_meta_token(self, checks: list, context: dict) -> None:
        token = context.get("meta_access_token") or os.getenv("META_ACCESS_TOKEN", "")
        if not token:
            checks.append(self._item("meta_token", "fail",
                                     "META_ACCESS_TOKEN no configurado"))
            return
        try:
            url = f"https://graph.facebook.com/debug_token?input_token={token}&access_token={token}"
            req = urllib.request.Request(url, headers={"User-Agent": "FactoryQA/0.1"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            info = data.get("data", {})
            if info.get("is_valid"):
                exp  = info.get("expires_at", 0)
                days = max(0, (exp - int(__import__("time").time())) // 86400) if exp else 0
                if exp and days < 7:
                    checks.append(self._item("meta_token", "warn",
                                             f"Token válido pero expira en {days} días"))
                else:
                    checks.append(self._item("meta_token", "pass",
                                             f"Token Meta válido — expira en {days} días" if exp else "Token Meta válido"))
            else:
                checks.append(self._item("meta_token", "fail",
                                         "Token Meta inválido o expirado"))
        except Exception as exc:
            checks.append(self._item("meta_token", "warn",
                                     f"No se pudo verificar token Meta: {exc}"))

    @staticmethod
    def _item(nombre: str, status: str, mensaje: str) -> dict:
        return {
            "nombre":   nombre,
            "status":   status,
            "semaforo": _SEMAFORO.get(status, status.upper()),
            "mensaje":  mensaje,
        }
