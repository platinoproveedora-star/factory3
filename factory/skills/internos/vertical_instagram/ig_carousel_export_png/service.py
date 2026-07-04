from __future__ import annotations

import importlib.util


class IgCarouselExportPngService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        slides = context.get("slides")
        if not isinstance(slides, list) or not slides:
            return {"ok": False, "error": "slides requerido"}
        backend = str(context.get("backend") or "playwright").strip()
        available = self._backend_available(backend)
        plan = {
            "backend": backend,
            "available": available,
            "expected_outputs": [f"slide_{idx:02d}.png" for idx, _ in enumerate(slides[:10], start=1)],
            "next_step": "instalar/configurar backend local" if not available else "renderizar PNG desde HTML/SVG",
        }
        if not available:
            return {"ok": False, "error": f"backend {backend} no disponible; no se agregan dependencias automaticamente", "data": {"plan": plan}}
        return {"ok": True, "data": {"plan": plan}}

    def _backend_available(self, backend: str) -> bool:
        if backend == "playwright":
            return importlib.util.find_spec("playwright") is not None
        if backend == "cairosvg":
            return importlib.util.find_spec("cairosvg") is not None
        return False
