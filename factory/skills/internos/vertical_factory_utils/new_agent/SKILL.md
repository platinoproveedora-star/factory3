---
name: new_agent
description: Crea agentes portables compatibles con Factory
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

Crear agentes portables de Factory y registrarlos en el registry de agentes.

## Entrada Esperada

Un diccionario `context` con:

- `nombre`
- `agent_id` opcional; si no viene, se genera UUID
- `mcps`
- `skills`
- `descripcion`
- `vertical`
- `dry_run`
- `base_dir`
- `memory`, `memoria` o `use_memory` opcional; acepta bool o texto tipo `si/no`
- `memory_table` opcional; default `agent_memory`

Cuando se pide memoria, `new_agent` solo deja metadata Supabase en el manifest/registry
y agrega un `next_steps` con `add_agent_memory_supabase`; no llama Supabase ni requiere
credenciales.

## Salida Esperada

Un diccionario con `ok`, `message` o `error`, y `data` con el plan o resultado.
