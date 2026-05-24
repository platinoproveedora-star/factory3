"""Service for wizard - manages conversational flows for Factory bots."""

from __future__ import annotations

FLOWS: dict = {
    "new_agent": {
        "skill": "new_agent",
        "steps": [
            {"key": "nombre", "question": "Como se llama el agente? (snake_case, ej: gestor_pedidos)"},
            {"key": "descripcion", "question": "Que hace este agente? Describelo con detalle."},
            {"key": "vertical", "question": "Vertical? (ventas, ops, factory...) - Enter para 'general'", "default": "general"},
            {"key": "memory", "question": "Quieres memoria Supabase? (si/no)", "default": "no", "type": "bool"},
        ],
    }
}

CANCEL_WORDS = {"/cancelar", "cancelar"}
YES_WORDS = {"si", "s\u00ed", "s", "yes", "y"}
NO_WORDS = {"no", "n"}


class WizardService:

    def ejecutar(self, context: dict) -> dict:
        flow_name = context.get("flow")
        if not flow_name:
            return {"ok": False, "error": "flow es requerido"}

        flow = FLOWS.get(flow_name)
        if not flow:
            return {"ok": False, "error": f"flow desconocido: {flow_name}"}

        text = context.get("text", "").strip()
        state = context.get("state", {})

        if not state:
            return self._start(flow, flow_name)

        if text.lower() in CANCEL_WORDS:
            return {"ok": True, "response": "Cancelado.", "state": {}, "done": False}

        if state.get("confirming"):
            return self._confirmar(flow, state, text)

        return self._step(flow, flow_name, state, text)

    def _start(self, flow: dict, flow_name: str) -> dict:
        first = flow["steps"][0]
        return {
            "ok": True,
            "response": first["question"],
            "state": {"flow": flow_name, "step": 0, "data": {}},
            "done": False,
        }

    def _step(self, flow: dict, flow_name: str, state: dict, text: str) -> dict:
        step_idx = state["step"]
        step_def = flow["steps"][step_idx]
        raw_value = text or step_def.get("default", "")
        value, error = self._parse_step_value(step_def, raw_value)

        if error:
            return {"ok": True, "response": f"{error} {step_def['question']}", "state": state, "done": False}

        if value == "":
            return {"ok": True, "response": f"Necesito una respuesta. {step_def['question']}", "state": state, "done": False}

        data = {**state["data"], step_def["key"]: value}
        next_step = step_idx + 1

        if next_step < len(flow["steps"]):
            next_q = flow["steps"][next_step]
            return {
                "ok": True,
                "response": next_q["question"],
                "state": {"flow": flow_name, "step": next_step, "data": data},
                "done": False,
            }

        resumen = "\n".join(f"- {k}: {v}" for k, v in data.items())
        return {
            "ok": True,
            "response": f"Resumen:\n{resumen}\n\nConfirmar? (si/no)",
            "state": {"flow": flow_name, "step": step_idx, "data": data, "confirming": True},
            "done": False,
        }

    def _confirmar(self, flow: dict, state: dict, text: str) -> dict:
        if text.lower() in YES_WORDS:
            return {
                "ok": True,
                "response": None,
                "state": {},
                "done": True,
                "skill": flow["skill"],
                "context": state["data"],
            }
        return {"ok": True, "response": "Cancelado.", "state": {}, "done": False}

    def _parse_step_value(self, step_def: dict, value: str) -> tuple[object, str | None]:
        if step_def.get("type") != "bool":
            return value, None
        normalized = str(value).strip().lower()
        if normalized in YES_WORDS:
            return True, None
        if normalized in NO_WORDS:
            return False, None
        return None, "Responde si o no."
