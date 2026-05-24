# vertical_chat_agents

Vertical para crear, configurar, operar y evaluar agentes conversacionales de
empresas. La configuracion vive por empresa en `companies/<EMPRESA>/agents` y
el runtime reusable vive en `factory/skills/internos/vertical_chat_agents`.

## Skills

| Skill | Funcion |
| --- | --- |
| `chat_agent_run` | Ejecuta el agente: carga config, knowledge, historial y llama IA. |
| `chat_agent_attitude_builder` | Define actitud humana, calida, consultiva y profesional. |
| `chat_agent_behavior_guardrails` | Genera reglas contra tono grosero, frio o riesgoso. |
| `chat_agent_prompt_builder` | Construye el system prompt final desde config y knowledge. |
| `chat_agent_config_builder` | Genera/actualiza JSON del agente y knowledge base inicial. |
| `chat_agent_response_evaluator` | Evalua calidad, tono, utilidad y riesgo de una respuesta. |
| `chat_agent_demo_builder` | Crea una demo conceptual del agente para ventas. |
| `chat_agent_lead_capture` | Extrae contacto y crea lead usando `vertical_sales`. |
| `chat_agent_conversation_orchestrator` | Orquesta runtime, evaluacion y captura de lead. |

## Principio

Los agentes pueden sentirse humanos en trato, pero no deben fingir ser una
persona real. Si el usuario pregunta, deben decir que son asesores virtuales.

## Reuso

- `vertical_sales` se usa para leads, score, pipeline, follow-up y reportes.
- `bot_inbox_router` y `bot_form_capture` se pueden usar para formularios y
  flujos multicanal.
