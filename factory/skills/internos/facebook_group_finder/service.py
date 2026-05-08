"""Busca grupos de Facebook en Google y los guarda en Supabase."""

from __future__ import annotations

import re
import time
import random

import httpx
from bs4 import BeautifulSoup

from factory.engine import SupabaseClient


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-MX,es;q=0.9",
}
_FB_GROUP_RE = re.compile(r"facebook\.com/groups/([^/?&#\"]+)")


class FacebookGroupFinderService:

    def ejecutar(self, context: dict) -> dict:
        keywords: list[str] = context.get("keywords") or []
        region:   str       = context.get("region", "")
        limit:    int       = min(int(context.get("limit", 20)), 50)
        guardar:  bool      = context.get("guardar", True)
        vertical: str       = context.get("vertical", "")

        if not keywords:
            return {"ok": False, "error": "keywords es requerido"}

        query   = " ".join(keywords)
        if region:
            query += f" {region}"
        query += " site:facebook.com/groups"

        grupos = self._scrape_google(query, limit)

        if not grupos:
            return {"ok": True, "data": {"grupos": [], "total": 0, "query": query}}

        if guardar:
            db = SupabaseClient({})
            for g in grupos:
                g["vertical"] = vertical
                g["region"]   = region
                existing = db.rest_select("fb_grupos", filters={"url": g["url"]}, select="id", limit=1)
                if not (existing.get("ok") and existing.get("data")):
                    db.rest_insert("fb_grupos", g)

        return {"ok": True, "data": {"grupos": grupos, "total": len(grupos), "query": query}}

    def _scrape_google(self, query: str, limit: int) -> list[dict]:
        grupos: list[dict] = []
        seen:   set[str]   = set()
        start  = 0

        while len(grupos) < limit:
            url    = f"https://www.google.com/search?q={httpx.URL('', params={'q': query}).params}&start={start}&hl=es"
            params = {"q": query, "start": start, "hl": "es", "num": 10}

            try:
                resp = httpx.get(
                    "https://www.google.com/search",
                    params=params,
                    headers=_HEADERS,
                    timeout=15,
                    follow_redirects=True,
                )
            except Exception as e:
                break

            if resp.status_code != 200:
                break

            soup    = BeautifulSoup(resp.text, "html.parser")
            nuevos  = self._extraer_grupos(soup, seen)

            if not nuevos:
                break

            grupos.extend(nuevos)
            start += 10
            time.sleep(random.uniform(2.0, 4.0))

        return grupos[:limit]

    def _extraer_grupos(self, soup: BeautifulSoup, seen: set[str]) -> list[dict]:
        resultados = []
        for a in soup.find_all("a", href=True):
            href  = a["href"]
            match = _FB_GROUP_RE.search(href)
            if not match:
                continue
            slug = match.group(1)
            url  = f"https://www.facebook.com/groups/{slug}"
            if url in seen:
                continue
            seen.add(url)

            titulo = a.get_text(strip=True) or slug
            desc   = ""
            parent = a.find_parent()
            if parent:
                desc = parent.get_text(separator=" ", strip=True)[:200]

            resultados.append({
                "url":         url,
                "slug":        slug,
                "nombre":      titulo[:120],
                "descripcion": desc,
                "activo":      True,
            })
        return resultados
