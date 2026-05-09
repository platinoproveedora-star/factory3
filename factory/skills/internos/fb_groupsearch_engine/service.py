"""Service for fb_groupsearch_engine — busca grupos públicos de Facebook.

Motor de búsqueda en capas:
  1. Meta Graph API (token requerido, datos reales)
  2. Web search      — pendiente: Google Custom Search / Bing
  3. Scraping        — pendiente: playwright/selenium
  4. Haiku IA        — fallback siempre activo, grupos plausibles
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

_CIUDADES = [
    "México", "CDMX", "Ciudad de México", "Mérida", "Monterrey",
    "Guadalajara", "Cancún", "Tijuana", "Puebla", "Veracruz",
    "Chihuahua", "León", "Querétaro", "Hermosillo", "Mexicali",
    "Chiapas", "Oaxaca", "Tabasco", "Yucatán", "Nuevo León",
    "Aguascalientes", "Sonora", "Sinaloa", "Tamaulipas", "Jalisco",
]


class FbGroupsearchEngineService:

    def ejecutar(self, context: dict) -> dict:
        tema = (context.get("tema_busqueda") or "").strip()
        if not tema:
            return {"ok": False, "error": "tema_busqueda es requerido"}

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}

        limite = int(context.get("limite") or 25)
        grupos, fuente = self._buscar(tema, context, limite)

        return {
            "ok": True,
            "message": f"{len(grupos)} grupos encontrados via {fuente}",
            "data": {
                "grupos":        grupos,
                "fuente":        fuente,
                "tema_busqueda": tema,
            },
        }

    # ── Orquestador de capas ──────────────────────────────────────────────────

    def _buscar(self, tema: str, context: dict, limite: int) -> tuple[list, str]:
        token = (
            os.getenv("META_ACCESS_TOKEN")
            or os.getenv("IG_ACCESS_TOKEN")
            or context.get("access_token")
            or ""
        ).strip()

        # Capa 1 — Meta Graph API
        if token:
            try:
                grupos = self._buscar_meta_api(tema, token, limite)
                if grupos:
                    return grupos, "meta_api"
            except Exception:
                pass

        # Capa 2 — Web search (futuro)
        # try:
        #     grupos = self._buscar_web(tema, limite)
        #     if grupos:
        #         return grupos, "web_search"
        # except NotImplementedError:
        #     pass

        # Capa 3 — Scraping (futuro)
        # try:
        #     grupos = self._buscar_scraping(tema, limite)
        #     if grupos:
        #         return grupos, "scraping"
        # except NotImplementedError:
        #     pass

        # Capa 4 — Haiku IA (fallback)
        return self._buscar_haiku(tema, limite), "ia_sugerido"

    # ── Implementaciones activas ──────────────────────────────────────────────

    def _buscar_meta_api(self, tema: str, token: str, limite: int = 25) -> list:
        version = os.getenv("IG_GRAPH_API_VERSION", "v25.0")
        params  = urllib.parse.urlencode({
            "type":         "group",
            "q":            tema,
            "fields":       "id,name,description,member_count,privacy",
            "access_token": token,
            "limit":        limite,
        })
        url = f"https://graph.facebook.com/{version}/search?{params}"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "FactoryFactory/0.1 (+https://github.com/)"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode())

        grupos = []
        for item in result.get("data", []):
            nombre = item.get("name", "")
            desc   = (item.get("description") or "")[:500]
            grupos.append({
                "grupo_nombre":        nombre,
                "grupo_url":           f"https://facebook.com/groups/{item.get('id', '')}",
                "descripcion":         desc,
                "miembros_estimados":  item.get("member_count"),
                "ubicacion_detectada": self._extract_location(nombre + " " + desc),
            })
        return grupos

    def _buscar_haiku(self, tema: str, limite: int = 25) -> list:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return []

        prompt = (
            f"Genera una lista de {limite} grupos públicos de Facebook que probablemente existan "
            f"sobre el tema: '{tema}'.\n"
            f"Para cada grupo: nombre realista, descripción corta (1 línea), "
            f"miembros estimados (número entero), ubicación geográfica si aplica.\n"
            f"Solo JSON válido sin bloques de código:\n"
            f'{{"grupos": [{{"nombre": "...", "descripcion": "...", "miembros": 1500, "ubicacion": "Mérida, Yucatán"}}]}}'
        )
        payload = {
            "model":      "claude-haiku-4-5-20251001",
            "max_tokens": 1024,
            "messages":   [{"role": "user", "content": prompt}],
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode(),
            headers={
                "content-type":      "application/json",
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                result = json.loads(r.read().decode())
            raw = (result.get("content") or [{}])[0].get("text", "").strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
                if raw.endswith("```"):
                    raw = raw[:-3]
            data   = json.loads(raw.strip())
            grupos = []
            for item in data.get("grupos", []):
                grupos.append({
                    "grupo_nombre":        item.get("nombre", ""),
                    "grupo_url":           "",
                    "descripcion":         item.get("descripcion", ""),
                    "miembros_estimados":  item.get("miembros"),
                    "ubicacion_detectada": item.get("ubicacion", ""),
                })
            return grupos
        except Exception:
            return []

    # ── Placeholders para extensión futura ───────────────────────────────────

    def _buscar_web(self, tema: str) -> list:
        """Web search via Google Custom Search API o Bing Web Search API.
        Query sugerida: site:facebook.com/groups "{tema}"
        """
        raise NotImplementedError

    def _buscar_scraping(self, tema: str) -> list:
        """Scraping directo con playwright o selenium.
        Usar solo si Meta API y web search no están disponibles.
        """
        raise NotImplementedError

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_location(self, text: str) -> str:
        tl = text.lower()
        for ciudad in _CIUDADES:
            if ciudad.lower() in tl:
                return ciudad
        return ""
