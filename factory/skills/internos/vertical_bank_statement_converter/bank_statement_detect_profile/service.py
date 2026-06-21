from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from _statement_common import list_profiles


class BankStatementDetectProfileService:
    def ejecutar(self, context: dict) -> dict:
        text_sample = str(context.get("text_sample") or "").strip()
        if not text_sample:
            return {"ok": False, "error": "text_sample requerido"}

        profiles = list_profiles()
        if not profiles:
            return {"ok": False, "error": "no hay perfiles disponibles"}

        best: dict | None = None
        best_score = 0.0

        for profile in profiles:
            markers: list[str] = profile.get("detect_markers") or []
            if not markers:
                continue
            hits = sum(1 for m in markers if m in text_sample)
            score = hits / len(markers)
            if score > best_score:
                best_score = score
                best = profile

        if not best or best_score == 0:
            return {"ok": False, "error": "perfil no soportado o PDF sin texto nativo suficiente"}

        return {
            "ok": True,
            "data": {
                "bank_profile": best["bank_profile"],
                "profile_version": best["profile_version"],
                "bank_name": best.get("bank_name", ""),
                "confidence": round(best_score, 4),
            },
        }
