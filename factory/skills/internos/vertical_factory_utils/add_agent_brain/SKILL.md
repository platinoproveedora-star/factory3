---
name: add_agent_brain
description: Agrega un brain Anthropic a un agente portable.
version: "0.1.0"
type: internal
entrypoint: skill.py
contract: run(context) -> dict
vertical: factory
permissions: []
dependencies: []
mcps: []
---

## Rol

Agregar `agent_brain.py` y `prompts/system.md` a un agente existente para que pueda responder mensajes con Claude Haiku.

## Entrada Esperada

Un diccionario `context` con:

- `agent_name`: nombre del agente registrado.
- `provider`: proveedor del modelo; por defecto `anthropic`.
- `model`: modelo; por defecto `claude-3-5-haiku-latest`.
- `system_prompt`: prompt del agente.
- `dry_run`: si es `true`, no escribe archivos.
- `base_dir`: carpeta base de Factory.

## Salida Esperada

Un diccionario con `ok`, `message` o `error`, y `data` con el plan o resultado.
