"""Service for fb_groupsearch_engine — busca grupos públicos de Facebook.

Motor de búsqueda en capas:
  1. Meta Graph API  — bloqueado (requiere groups_access_member_info)
  2. Web search      — activo: Anthropic web_search_20250305 built-in tool
  3. Scraping        — pendiente: playwright/selenium
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

        limite       = int(context.get("limite") or 25)
        min_miembros = int(context.get("min_miembros") or 0)
        grupos, fuente = self._buscar(tema, context, limite)

        if min_miembros > 0:
            # miembros_estimados=None or 0 means unknown — keep it (don't filter out)
            grupos = [
                g for g in grupos
                if not g.get("miembros_estimados") or g["miembros_estimados"] >= min_miembros
            ]

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
        # Capa 1 — Meta Graph API (bloqueado — requiere permiso groups_access_member_info)
        # token = (os.getenv("META_ACCESS_TOKEN") or os.getenv("IG_ACCESS_TOKEN") or "").strip()
        # if token:
        #     try:
        #         grupos = self._buscar_meta_api(tema, token, limite)
        #         if grupos:
        #             return grupos, "meta_api"
        #     except Exception:
        #         pass

        # Capa 2 — Web search via Anthropic built-in web_search_20250305
        try:
            grupos = self._buscar_web(tema, limite)
            if grupos:
                return grupos, "web_search"
        except Exception:
            pass

        # Capa 3 — Scraping (pendiente: playwright/selenium)
        # try:
        #     grupos = self._buscar_scraping(tema, limite)
        #     if grupos:
        #         return grupos, "scraping"
        # except NotImplementedError:
        #     pass

        return [], "sin_resultados"

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

        # ~150 tokens por grupo en JSON; mínimo 1024, máximo 8192
        max_tokens = min(8192, max(1024, limite * 160))

        prompt = (
            f"Genera una lista de exactamente {limite} grupos públicos de Facebook que probablemente existan "
            f"sobre el tema: '{tema}'.\n"
            f"Para cada grupo: nombre realista, descripción corta (1 línea), "
            f"miembros estimados (número entero real, no pongas 0), ubicación geográfica si aplica.\n"
            f"Solo JSON válido sin bloques de código:\n"
            f'{{"grupos": [{{"nombre": "...", "descripcion": "...", "miembros": 1500, "ubicacion": "Mérida, Yucatán"}}]}}'
        )
        payload = {
            "model":      "claude-haiku-4-5-20251001",
            "max_tokens": max_tokens,
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

    # ── Implementación web search ─────────────────────────────────────────────

    def _buscar_web(self, tema: str, limite: int = 25) -> list:
        """Anthropic built-in web_search_20250305 — busca grupos reales de Facebook."""
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return []

        prompt = (
            f"Busca grupos públicos de Facebook sobre: '{tema}'.\n"
            f"Necesito encontrar {limite} grupos reales. Busca en Facebook directamente y en páginas "
            f"que listan grupos (groupsforexpats, findmyfbgroups, etc.).\n"
            f"Para cada grupo extrae: nombre, URL exacta de Facebook "
            f"(https://www.facebook.com/groups/...), descripción breve, "
            f"número de miembros si aparece, y ubicación geográfica si aplica.\n"
            f"Devuelve ÚNICAMENTE JSON válido, sin bloques de código ni texto extra:\n"
            f'{{"grupos": [{{"nombre": "...", "url": "https://www.facebook.com/groups/...", '
            f'"descripcion": "...", "miembros": 1500, "ubicacion": "Ciudad, País"}}]}}'
        )

        payload = {
            "model":      "claude-sonnet-4-6",
            "max_tokens": 4096,
            "tools":      [{"type": "web_search_20250305", "name": "web_search"}],
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
        with urllib.request.urlopen(req, timeout=90) as r:
            result = json.loads(r.read().decode())

        raw = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                raw += block.get("text", "")
        raw = raw.strip()

        # Extract JSON from the response (handles prose before/after and code fences)
        start = raw.find("{")
        end   = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return []
        raw = raw[start : end + 1]

        data   = json.loads(raw)
        grupos = []
        for item in data.get("grupos", []):
            url = item.get("url", "")
            if not url.startswith("http"):
                url = ""
            grupos.append({
                "grupo_nombre":        item.get("nombre", ""),
                "grupo_url":           url,
                "descripcion":         item.get("descripcion", ""),
                "miembros_estimados":  item.get("miembros"),
                "ubicacion_detectada": item.get("ubicacion", ""),
            })
        return grupos

    # ── Placeholders para extensión futura ───────────────────────────────────

    def _buscar_scraping(self, tema: str) -> list:
        """Scraping directo con playwright o selenium."""
        raise NotImplementedError

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_location(self, text: str) -> str:
        tl = text.lower()
        for ciudad in _CIUDADES:
            if ciudad.lower() in tl:
                return ciudad
        return ""
