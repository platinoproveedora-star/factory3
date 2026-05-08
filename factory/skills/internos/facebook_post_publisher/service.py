"""Publica un post en un grupo de Facebook via Playwright. Un grupo por llamada."""

from __future__ import annotations

import os
import time
import random
from datetime import datetime, timezone


class FacebookPostPublisherService:

    def ejecutar(self, context: dict) -> dict:
        grupo_url: str  = context.get("grupo_url") or ""
        texto:     str  = context.get("texto") or ""
        dry_run:   bool = context.get("dry_run", True)
        headless:  bool = context.get("headless", True)
        email:     str  = context.get("fb_email") or os.getenv("FB_EMAIL", "")
        password:  str  = context.get("fb_password") or os.getenv("FB_PASSWORD", "")

        if not grupo_url:
            return {"ok": False, "error": "grupo_url es requerido"}
        if not texto:
            return {"ok": False, "error": "texto es requerido"}

        if dry_run:
            return self._dry_run(grupo_url, texto)

        if not email or not password:
            return {"ok": False, "error": "FB_EMAIL y FB_PASSWORD son requeridos para publicar"}

        return self._publicar(grupo_url, texto, email, password, headless)

    def _dry_run(self, grupo_url: str, texto: str) -> dict:
        return {
            "ok": True,
            "data": {
                "dry_run":    True,
                "grupo_url":  grupo_url,
                "texto":      texto,
                "timestamp":  datetime.now(timezone.utc).isoformat(),
                "mensaje":    "dry_run activo — no se publicó nada. Configura FB_EMAIL y FB_PASSWORD y pasa dry_run: false para publicar.",
            },
        }

    def _publicar(self, grupo_url: str, texto: str, email: str, password: str, headless: bool) -> dict:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {"ok": False, "error": "Playwright no instalado. Ejecuta: pip install playwright && playwright install chromium"}

        resultado = {"grupo_url": grupo_url, "publicado": False, "timestamp": datetime.now(timezone.utc).isoformat()}

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

                # Navegar al grupo
                page.goto(grupo_url, wait_until="networkidle")
                self._delay(2, 4)

                # Hacer click en el campo de publicar
                post_box = page.locator("[data-pagelet='GroupFeed'] [role='button']").first
                if not post_box.is_visible():
                    post_box = page.get_by_placeholder("Escribe algo...").first
                post_box.click()
                self._delay()

                # Escribir el texto
                page.keyboard.type(texto, delay=random.randint(40, 90))
                self._delay(1, 2)

                # Publicar
                publish_btn = page.get_by_role("button", name="Publicar")
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
