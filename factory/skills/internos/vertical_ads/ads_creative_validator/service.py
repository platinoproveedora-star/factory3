"""Valida formatos, proporciones, duración y tamaño del asset por plataforma. Sin IA — reglas fijas."""
from __future__ import annotations

_SPECS: dict = {
    "meta": {
        "imagen": {"proporciones": ["1:1", "1.91:1", "4:5"], "peso_max_mb": 30, "formatos": ["jpg", "png", "gif"], "texto_max_pct": 20},
        "video":  {"proporciones": ["1:1", "4:5", "9:16", "16:9"], "duracion_max_s": 241, "peso_max_mb": 4096, "formatos": ["mp4", "mov"]},
        "carrusel": {"proporciones": ["1:1"], "tarjetas_max": 10, "peso_max_mb": 30, "formatos": ["jpg", "png"]},
        "story": {"proporciones": ["9:16"], "duracion_max_s": 15, "peso_max_mb": 4096, "formatos": ["mp4", "jpg", "png"]},
    },
    "google": {
        "imagen": {"proporciones": ["1:1", "1.91:1"], "peso_max_mb": 5, "formatos": ["jpg", "png", "gif"]},
        "video":  {"proporciones": ["16:9"], "duracion_max_s": 60, "peso_max_mb": 256, "formatos": ["mp4"]},
    },
    "tiktok": {
        "video":  {"proporciones": ["9:16"], "duracion_max_s": 60, "duracion_min_s": 5, "peso_max_mb": 500, "formatos": ["mp4"]},
    },
    "linkedin": {
        "imagen": {"proporciones": ["1.91:1", "1:1"], "peso_max_mb": 5, "formatos": ["jpg", "png"]},
        "video":  {"proporciones": ["16:9", "1:1", "9:16"], "duracion_max_s": 1800, "peso_max_mb": 200, "formatos": ["mp4"]},
    },
}


class AdsCreativeValidatorService:

    def ejecutar(self, context: dict) -> dict:
        plataforma = context.get("plataforma", "").strip().lower()
        formato    = context.get("formato", "").strip().lower()
        proporcion = context.get("proporcion", "").strip()
        peso_mb    = context.get("peso_mb")
        duracion_s = context.get("duracion_s")
        extension  = context.get("extension", "").strip().lower().lstrip(".")

        if not plataforma:
            return {"ok": False, "error": "plataforma requerida"}
        if not formato:
            return {"ok": False, "error": "formato requerido (imagen/video/carrusel/story)"}

        plat_specs = _SPECS.get(plataforma)
        if not plat_specs:
            return {"ok": False, "error": f"plataforma no soportada — válidas: {', '.join(_SPECS)}"}

        fmt_specs = plat_specs.get(formato)
        if not fmt_specs:
            return {"ok": False, "error": f"formato '{formato}' no válido para {plataforma}"}

        errores = []
        advertencias = []

        if proporcion and proporcion not in fmt_specs.get("proporciones", []):
            errores.append(f"Proporción {proporcion} no válida — aceptadas: {fmt_specs['proporciones']}")

        if peso_mb is not None and peso_mb > fmt_specs.get("peso_max_mb", 9999):
            errores.append(f"Peso {peso_mb}MB excede límite de {fmt_specs['peso_max_mb']}MB")

        if duracion_s is not None:
            if "duracion_max_s" in fmt_specs and duracion_s > fmt_specs["duracion_max_s"]:
                errores.append(f"Duración {duracion_s}s excede límite de {fmt_specs['duracion_max_s']}s")
            if "duracion_min_s" in fmt_specs and duracion_s < fmt_specs["duracion_min_s"]:
                errores.append(f"Duración {duracion_s}s menor al mínimo de {fmt_specs['duracion_min_s']}s")

        if extension and extension not in fmt_specs.get("formatos", []):
            errores.append(f"Formato .{extension} no aceptado — válidos: {fmt_specs['formatos']}")

        if plataforma == "meta" and formato == "imagen":
            texto_pct = context.get("texto_pct")
            if texto_pct is not None and texto_pct > 20:
                advertencias.append(f"Texto ocupa {texto_pct}% — Meta recomienda máx 20%")

        aprobado = len(errores) == 0
        return {"ok": True, "data": {
            "aprobado":     aprobado,
            "plataforma":   plataforma,
            "formato":      formato,
            "errores":      errores,
            "advertencias": advertencias,
            "specs_referencia": fmt_specs,
        }}
