"""Publica oferta de empleo en Facebook Marketplace via Playwright."""

from __future__ import annotations

import os
import time
import random
from datetime import datetime, timezone


class FacebookMarketplacePosterService:

    def ejecutar(self, context: dict) -> dict:
        titulo:      str   = context.get("titulo") or ""
        descripcion: str   = context.get("descripcion") or ""
        ubicacion:   str   = context.get("ubicacion") or ""
        salario:     str   = context.get("salario") or ""
        contacto:    str   = context.get("contacto") or ""
        dry_run:     bool  = context.get("dry_run", True)
        headless:    bool  = context.get("headless", True)
        email:       str   = context.get("fb_email") or os.getenv("FB_EMAIL", "")
        password:    str   = context.get("fb_password") or os.getenv("FB_PASSWORD", "")

        if not titulo:
            return {"ok": False, "error": "titulo es requerido"}
        if not descripcion:
            return {"ok": False, "error": "descripcion es requerido"}

        if dry_run:
            return self._dry_run(titulo, descripcion, ubicacion, salario, contacto)

        if not email or not password:
            return {"ok": False, "error": "FB_EMAIL y FB_PASSWORD requeridos para publicar"}

        return self._publicar(titulo, descripcion, ubicacion, salario, contacto, email, password, headless)

    def _dry_run(self, titulo, descripcion, ubicacion, salario, contacto) -> dict:
        return {
            "ok": True,
            "data": {
                "dry_run":    True,
                "titulo":     titulo,
                "ubicacion":  ubicacion,
                "salario":    salario,
                "timestamp":  datetime.now(timezone.utc).isoformat(),
                "mensaje":    "dry_run activo — configura FB_EMAIL, FB_PASSWORD y pasa dry_run: false para publicar en Marketplace.",
            },
        }

    def _publicar(self, titulo, descripcion, ubicacion, salario, contacto, email, password, headless) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {"ok": False, "error": "Playwright no instalado. Ejecuta: pip install playwright && playwright install chromium"}

        resultado = {"publicado": False, "timestamp": datetime.now(timezone.utc).isoformat(), "canal": "marketplace"}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                ctx = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    locale="es-MX",
                    timezone_id="America/Merida",
                )
                page = ctx.new_page()

                # Login
                page.goto("https://www.facebook.com/login", wait_until="networkidle")
                self._delay()
                page.fill("#email", email)
                self._delay()
                page.fill("#pass", password)
                self._delay()
                page.click("[name='login']")
                page.wait_for_load_state("networkidle")
                self._delay(2, 4)

                if "login" in page.url:
                    browser.close()
                    return {"ok": False, "error": "Login fallido — verifica credenciales FB"}

                # Navegar a Marketplace > Crear anuncio de empleo
                page.goto("https://www.facebook.com/marketplace/create/job", wait_until="networkidle")
                self._delay(2, 4)

                # Titulo
                title_field = page.get_by_label("Título del empleo")
                if not title_field.is_visible():
                    title_field = page.locator("input[placeholder*='título']").first
                title_field.fill(titulo)
                self._delay()

                # Descripcion
                desc_field = page.get_by_label("Descripción")
                if not desc_field.is_visible():
                    desc_field = page.locator("textarea").first
                desc_field.fill(f"{descripcion}\n\nContacto: {contacto}" if contacto else descripcion)
                self._delay()

                # Ubicacion
                if ubicacion:
                    loc_field = page.get_by_label("Ubicación")
                    if loc_field.is_visible():
                        loc_field.fill(ubicacion)
                        self._delay()

                # Salario
                if salario:
                    sal_field = page.get_by_label("Salario")
                    if sal_field.is_visible():
                        sal_field.fill(salario)
                        self._delay()

                # Publicar
                publish_btn = page.get_by_role("button", name="Publicar")
                if not publish_btn.is_visible():
                    publish_btn = page.get_by_role("button", name="Siguiente")
                publish_btn.click()
                page.wait_for_load_state("networkidle")
                self._delay(2, 3)

                resultado["publicado"] = True
                browser.close()

        except Exception as e:
            resultado["error"] = str(e)
            return {"ok": False, "data": resultado, "error": str(e)}

        return {"ok": True, "data": resultado}

    def _delay(self, min_s: float = 0.8, max_s: float = 2.0) -> None:
        time.sleep(random.uniform(min_s, max_s))
