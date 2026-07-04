from __future__ import annotations


_THEMES = {
    "teal_science": {
        "background": "#eef7f6",
        "panel": "#ffffff",
        "ink": "#12343b",
        "muted": "#48666b",
        "accent": "#0f766e",
        "accent_2": "#256d85",
        "line": "#b8d8d4",
        "soft": "#dff4f1",
    },
    "editorial_blue": {
        "background": "#eef2f7",
        "panel": "#ffffff",
        "ink": "#172033",
        "muted": "#526071",
        "accent": "#2563eb",
        "accent_2": "#14b8a6",
        "line": "#cbd5e1",
        "soft": "#e0f2fe",
    },
    "warm_clinical": {
        "background": "#f7f5ef",
        "panel": "#ffffff",
        "ink": "#2f3a32",
        "muted": "#687063",
        "accent": "#0f766e",
        "accent_2": "#b45309",
        "line": "#d8d2c3",
        "soft": "#edf6df",
    },
}


class IgCarouselThemeGuardService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        theme = str(context.get("theme") or "teal_science").strip()
        palette = dict(_THEMES.get(theme) or _THEMES["teal_science"])
        palette.update(context.get("colors") if isinstance(context.get("colors"), dict) else {})
        warnings = []
        if palette.get("ink", "").lower() in {"#000", "#000000", "black"}:
            warnings.append("ink negro puro reemplazado por tinta editorial compatible")
            palette["ink"] = _THEMES["teal_science"]["ink"]
        template = context.get("template") if isinstance(context.get("template"), dict) else {}
        guarded_template = {**template, "palette": {**(template.get("palette") if isinstance(template.get("palette"), dict) else {}), **palette}}
        return {"ok": True, "data": {"theme": theme, "palette": palette, "template": guarded_template, "warnings": warnings}}
