"""Service for identidad_visual — generates visual identity assets via FAL API."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_LOGO_PROMPT = (
    "Professional logo for '{nombre}', a company offering {productos} in {ubicacion}. "
    "Primary color: {paleta_primaria}. Secondary color: {paleta_secundaria}. "
    "Style: {tono}. Square format, transparent background preferred, company name only."
)
_FB_COVER_PROMPT = (
    "Facebook cover photo for '{nombre}', a company offering {productos} in {ubicacion}. "
    "Primary color: {paleta_primaria}. Secondary color: {paleta_secundaria}. "
    "Style: {tono}. Landscape 820x312 format, professional, no text overlay."
)
_IG_COVER_PROMPT = (
    "Instagram profile cover for '{nombre}', a company offering {productos} in {ubicacion}. "
    "Primary color: {paleta_primaria}. Secondary color: {paleta_secundaria}. "
    "Style: {tono}. Square 1080x1080 format, clean and professional."
)

_IMAGE_SIZES = {
    "logo":     "square_hd",
    "fb_cover": "landscape_4_3",
    "ig_cover": "square_hd",
}


class IdentidadVisualService:

    def ejecutar(self, context: dict) -> dict:
        empresa_id = (context.get("empresa_id") or "").strip()
        nombre = (context.get("nombre_empresa") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido"}
        if not nombre:
            return {"ok": False, "error": "nombre_empresa requerido"}

        fal_key = (
            context.get("fal_key") or os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY") or ""
        ).strip()
        if not fal_key:
            return {"ok": False, "error": "FAL_KEY no configurada"}

        supabase_url = (context.get("supabase_url") or os.getenv("SUPABASE_URL") or "").rstrip("/")
        supabase_key = context.get("supabase_key") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
        if not supabase_url or not supabase_key:
            return {"ok": False, "error": "SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY requeridos"}

        productos_list = context.get("productos_o_servicios") or []
        productos = ", ".join(str(p) for p in productos_list) if productos_list else "sus productos"
        ubicacion = (context.get("ubicacion") or "Mexico").strip()
        paleta_primaria = (context.get("paleta_primaria") or "#FFD700").strip()
        paleta_secundaria = (context.get("paleta_secundaria") or "#333333").strip()
        tono = (context.get("tono_marca") or "profesional, confiable").strip()

        model_primary = (context.get("modelo_imagen") or "fal-ai/nano-banana-pro").strip()
        model_fallback = (context.get("modelo_imagen_fallback") or "fal-ai/recraft/v4/pro/text-to-image").strip()

        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": {
                "empresa_id": empresa_id,
                "modelo_primario": model_primary,
                "estado_aprobacion": "pendiente",
            }}

        vars_ = {
            "nombre": nombre,
            "productos": productos,
            "ubicacion": ubicacion,
            "paleta_primaria": paleta_primaria,
            "paleta_secundaria": paleta_secundaria,
            "tono": tono,
        }

        logo_url, modelo_usado, logo_err = self._generar(
            fal_key, model_primary, model_fallback,
            _LOGO_PROMPT.format(**vars_), _IMAGE_SIZES["logo"],
        )
        if not logo_url:
            return {"ok": False, "error": f"FAL logo: {logo_err}"}

        fb_url, _, _ = self._generar(
            fal_key, model_primary, model_fallback,
            _FB_COVER_PROMPT.format(**vars_), _IMAGE_SIZES["fb_cover"],
        )
        ig_url, _, _ = self._generar(
            fal_key, model_primary, model_fallback,
            _IG_COVER_PROMPT.format(**vars_), _IMAGE_SIZES["ig_cover"],
        )

        row = {
            "empresa_id": empresa_id,
            "logo_url": logo_url,
            "portada_fb_url": fb_url,
            "portada_ig_url": ig_url,
            "paleta_primaria": paleta_primaria,
            "paleta_secundaria": paleta_secundaria,
            "tono_marca": tono,
            "modelo_usado": modelo_usado,
            "estado_aprobacion": "pendiente",
        }

        try:
            saved = self._supabase_insert("fb_identity", row, supabase_url, supabase_key)
            record_id = saved[0].get("id") if saved else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return {"ok": False, "error": f"Supabase {exc.code}: {body[:300]}", "data": row}
        except Exception as exc:
            return {"ok": False, "error": f"Supabase: {exc}", "data": row}

        return {"ok": True, "data": {**row, "id": record_id}}

    def _generar(
        self,
        fal_key: str,
        model_primary: str,
        model_fallback: str,
        prompt: str,
        image_size: str,
    ) -> tuple[str | None, str, str | None]:
        last_error = None
        for model_id in (model_primary, model_fallback):
            try:
                result = self._call_fal(fal_key, model_id, {"prompt": prompt, "image_size": image_size})
                # Try common FAL response shapes
                url = (
                    (result.get("images") or [{}])[0].get("url")
                    or (result.get("image") or {}).get("url")
                    or result.get("url")
                )
                if url:
                    return url, model_id, None
                last_error = f"modelo {model_id}: respuesta sin url — keys={list(result.keys())}"
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")[:300]
                last_error = f"modelo {model_id}: HTTP {exc.code} — {body}"
            except Exception as exc:
                last_error = f"modelo {model_id}: {exc}"
        return None, model_fallback, last_error

    def _call_fal(self, fal_key: str, model_id: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"https://fal.run/{model_id}",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Key {fal_key}",
                "Content-Type": "application/json",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())

    def _supabase_insert(self, table: str, row: dict, url: str, key: str) -> list:
        req = urllib.request.Request(
            f"{url}/rest/v1/{table}",
            data=json.dumps(row).encode(),
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
                "User-Agent": "FactoryFactory/0.1 (+https://github.com/)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
