"""Runtime genérico de chat agents — carga config, construye prompt y llama Haiku."""
from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

# factory3 root (6 niveles desde service.py en vertical_chat_agents/chat_agent_run/)
_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent

_VALID_ACTIONS = {"reply", "capture_lead", "escalate_human", "end_conversation"}
_ACTION_RE     = re.compile(r'\[ACCION:([a-z_]+)\]', re.IGNORECASE)

_HAIKU_MODEL   = "claude-haiku-4-5-20251001"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


class ChatAgentRunService:

    def ejecutar(self, context: dict) -> dict:
        agent_id   = context.get("agent_id", "AGT-001")
        message    = (context.get("message") or "").strip()
        history    = context.get("history") or []
        dry_run    = context.get("dry_run", True)

        # Ruta de agentes: context > company_id > default EMP_ESTOIKOLAB
        company_id  = context.get("company_id", "EMP_ESTOIKOLAB")
        agents_root = Path(context.get("agents_root") or (_ROOT / "companies" / company_id / "agents"))
        company_root = agents_root.parent

        if not message:
            return {"ok": False, "error": "message requerido"}

        # 1. Cargar config del agente
        config = self._load_config(agent_id, agents_root)
        if not config:
            return {"ok": False, "error": f"Agente no encontrado: {agent_id}"}

        # 2. Cargar base de conocimiento
        knowledge = self._load_knowledge(config, company_root)

        # 3. Verificar límite de turnos
        max_turns   = config.get("max_turns", 20)
        turn_count  = len([h for h in history if h.get("role") == "user"])
        if turn_count >= max_turns:
            farewell    = f"Ha sido un placer atenderte. ¡Hasta pronto! 👋"
            new_history = list(history) + [
                {"role": "user",      "content": message},
                {"role": "assistant", "content": farewell},
            ]
            return {"ok": True, "data": {
                "response": farewell,
                "action":   "end_conversation",
                "turn":     turn_count,
                "history":  new_history,
            }}

        # 4. Construir system prompt
        system_prompt = self._build_prompt(config, knowledge)

        # dry_run: retorna preview sin llamar a Haiku
        if dry_run:
            return {"ok": True, "data": {
                "response": f"[dry_run] Agente: {config.get('name')} | Turno {turn_count + 1}",
                "action":   "reply",
                "turn":     turn_count + 1,
                "history":  history,
            }}

        # 5. Preparar historial (últimos 20 mensajes = 10 turnos)
        messages = [{"role": h["role"], "content": h["content"]} for h in history[-20:]]
        messages.append({"role": "user", "content": message})

        # 6. Llamar a Haiku
        raw = self._call_haiku(system_prompt, messages)
        if raw is None:
            return {"ok": False, "error": "Error al llamar a Haiku — verifica ANTHROPIC_API_KEY"}

        # 7. Parsear acción y limpiar respuesta
        response, action = self._parse_action(raw, config)

        # 8. Actualizar historial
        new_history = list(history)
        new_history.append({"role": "user",      "content": message})
        new_history.append({"role": "assistant",  "content": response})

        return {"ok": True, "data": {
            "response": response,
            "action":   action,
            "turn":     turn_count + 1,
            "history":  new_history,
        }}

    # ── helpers ───────────────────────────────────────────────────────────────

    def _load_config(self, agent_id: str, agents_root: Path) -> dict | None:
        path = agents_root / f"{agent_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _load_knowledge(self, config: dict, company_root: Path) -> str:
        kf = config.get("knowledge_file")
        if not kf:
            return ""
        path = company_root / kf
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return ""

    def _build_prompt(self, config: dict, knowledge: str) -> str:
        name      = config.get("name", "Asistente")
        persona   = config.get("persona", "Soy un asistente virtual.")
        tone      = config.get("tone", "profesional_amigable")
        objective = config.get("objective", "atención")
        rules     = config.get("rules") or []
        limits    = config.get("limits") or []
        actions   = config.get("allowed_actions") or ["reply"]

        lines = [
            f"Eres {name}. {persona}",
            f"\nTONO: {tone}",
            f"OBJETIVO: {objective}",
        ]

        if rules:
            lines.append("\nREGLAS:")
            lines.extend(f"- {r}" for r in rules)

        if limits:
            lines.append("\nLÍMITES:")
            lines.extend(f"- {l}" for l in limits)

        if knowledge:
            lines.append(f"\nCONOCIMIENTO BASE:\n{knowledge}")

        _action_docs = {
            "reply":            "[ACCION:reply] — respuesta conversacional normal",
            "capture_lead":     "[ACCION:capture_lead] — el usuario quiere cotizar, comprar o dejar sus datos",
            "escalate_human":   "[ACCION:escalate_human] — el usuario pide hablar con una persona",
            "end_conversation": "[ACCION:end_conversation] — la conversación terminó de forma natural",
        }
        lines.append("\n---")
        lines.append("INSTRUCCIÓN IMPORTANTE: Al final de CADA respuesta agrega exactamente una etiqueta:")
        all_actions = list(dict.fromkeys(["reply"] + list(actions)))  # reply siempre disponible
        for a in all_actions:
            if a in _action_docs:
                lines.append(_action_docs[a])
        lines.append("La etiqueta debe ser la última línea de tu respuesta, sin texto después.")

        return "\n".join(lines)

    def _call_haiku(self, system: str, messages: list) -> str | None:
        payload = {
            "model":      _HAIKU_MODEL,
            "max_tokens": 512,
            "system":     system,
            "messages":   messages,
        }
        req = urllib.request.Request(
            _ANTHROPIC_URL,
            data=json.dumps(payload).encode(),
            headers={
                "content-type":      "application/json",
                "x-api-key":         os.getenv("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = json.loads(r.read().decode())
                return body["content"][0]["text"]
        except Exception:
            return None

    def _parse_action(self, raw: str, config: dict) -> tuple[str, str]:
        match   = _ACTION_RE.search(raw)
        action  = "reply"
        if match:
            candidate = match.group(1).lower()
            allowed   = set(config.get("allowed_actions") or []) | {"reply"}
            if candidate in _VALID_ACTIONS and candidate in allowed:
                action = candidate
        response = _ACTION_RE.sub("", raw).strip()
        return response, action
