"""Heuristic evaluator for chat agent responses."""
from __future__ import annotations


_BAD = ["obviamente", "ya te dije", "no entiendes", "eso no", "imposible", "no puedo ayudarte con eso"]
_GOOD = ["entiendo", "claro", "con gusto", "tiene sentido", "podemos", "si te parece"]


class ChatAgentResponseEvaluatorService:
    def ejecutar(self, context: dict) -> dict:
        response = (context.get("response") or "").strip()
        if not response:
            return {"ok": False, "error": "response requerido"}
        lower = response.lower()
        issues = []
        score = 100
        if any(x in lower for x in _BAD):
            issues.append("posible tono seco o confrontativo")
            score -= 30
        if len(response) > 1200:
            issues.append("respuesta demasiado larga")
            score -= 15
        if "?" not in response and not any(x in lower for x in ["comparteme", "cuentame", "puedo"]):
            issues.append("no invita a siguiente paso")
            score -= 10
        if not any(x in lower for x in _GOOD):
            issues.append("poca calidez explicita")
            score -= 10
        if "[accion:" in lower:
            issues.append("etiqueta tecnica visible al usuario")
            score -= 20
        score = max(0, min(100, score))
        return {"ok": True, "data": {
            "score": score,
            "passed": score >= int(context.get("min_score", 75)),
            "issues": issues,
            "recommendation": "usar" if score >= 75 else "revisar tono antes de enviar"
        }}
