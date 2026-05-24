# EMP_ESTOIKOLAB — Arquitectura de agentes

## Qué es Estoiko Lab

Agencia de marketing digital que opera como **fábrica interna de chat agents**.
Diseña, configura y opera agentes de conversación con IA para sus clientes.
Cada agente vive embebido en la web del cliente como un widget de chat.

## Principio de operación

Un solo skill genérico (`chat_agent_run`) corre cualquier agente.
La personalidad, reglas y conocimiento de cada agente viven en su `agent_config.json`.
Estoiko Lab gestiona los configs; los clientes solo ponen el snippet en su web.

## Capas

| Capa | Vive en | Contenido |
|---|---|---|
| Runtime genérico | `factory/skills/internos/vertical_chat_agents/` | Skills reutilizables para cualquier agente |
| Config por agente | `companies/EMP_ESTOIKOLAB/agents/` | Un JSON por agente/cliente |
| Conocimiento | `companies/EMP_ESTOIKOLAB/knowledge/` | Base de conocimiento por agente (texto plano) |
| Endpoint | `factory_api.py` → `POST /chat/{agent_id}` | Entrada HTTP del widget |
| Widget | `companies/EMP_ESTOIKOLAB/widget/` | Snippet JS embebible |

## Estructura de carpetas

```
companies/EMP_ESTOIKOLAB/
  company.config.json
  AGENTS_ARCHITECTURE.md          ← este archivo
  agents/
    agent_template.json           ← plantilla base para nuevos agentes
  knowledge/
    README.md                     ← cómo agregar conocimiento
  widget/
    chat.js                       ← widget vanilla JS
    chat.css                      ← estilos del bubble
    README.md                     ← instrucciones de embed
```

## Flujo de una conversación

```
Usuario escribe en widget
  → POST /chat/{agent_id}  { session_id, message }
  → chat_agent_run
      → carga agent_config.json
      → carga historial de sesión (bot_states)
      → construye system prompt (config + knowledge)
      → llama Haiku
      → detecta acción (reply / capture_lead / escalate / end)
      → guarda historial
  → { response, action, data }
  → widget muestra respuesta
```

## Acciones que puede ejecutar un agente

| Acción | Qué hace |
|---|---|
| `reply` | Respuesta conversacional normal |
| `capture_lead` | Activa formulario de captura en el widget |
| `escalate_human` | Informa al usuario que lo deriva a un humano |
| `end_conversation` | Cierra la sesión con un mensaje de despedida |

## Estructura del agent_config.json

```json
{
  "agent_id": "AGT-001",
  "client_name": "Empresa del cliente",
  "name": "Nombre del agente",
  "objective": "ventas | atencion | faqs | agendado | soporte",
  "persona": "Descripción de quién es el agente y para quién trabaja",
  "tone": "profesional | amigable | entusiasta | técnico",
  "welcome_message": "Mensaje de bienvenida",
  "language": "es",
  "rules": ["regla 1", "regla 2"],
  "limits": ["no hacer X", "no prometer Y"],
  "allowed_actions": ["reply", "capture_lead", "escalate_human"],
  "lead_fields": ["nombre", "email", "telefono"],
  "knowledge_file": "knowledge/cliente_x.txt",
  "max_turns": 20,
  "status": "active"
}
```

## Primer agente MVP

El primer agente a construir validará todo el flujo end-to-end:
- Config en `agents/agent_template.json`
- Skill `chat_agent_run` funcional
- Endpoint `POST /chat/{agent_id}` en factory_api.py
- Widget JS mínimo con bubble y panel de chat

Una vez validado con un cliente real de Estoiko Lab,
se puede replicar para cada nuevo cliente en minutos.

## Skills MVP (orden de construcción)

| # | Skill | Estado |
|---|---|---|
| 1 | `vertical_chat_agents/chat_agent_run` | Pendiente |
| 2 | Endpoint `POST /chat/{agent_id}` en factory_api.py | Pendiente |
| 3 | Widget JS básico | Pendiente |
| 4 | `vertical_chat_agents/chat_agent_test_simulator` | Pendiente |
