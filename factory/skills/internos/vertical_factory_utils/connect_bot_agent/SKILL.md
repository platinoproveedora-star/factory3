---
name: connect_bot_agent
description: Conecta un bot Factory con un agente por defecto.
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

Declarar la relacion entre un bot y un agente para que el bot pueda enrutar mensajes al agente conectado.

## Entrada Esperada

Un diccionario `context` con:

- `bot_name`: nombre del bot registrado.
- `agent_name`: nombre del agente registrado.
- `mode`: modo de conexion; por defecto `chat`.
- `dry_run`: si es `true`, no escribe archivos.
- `base_dir`: carpeta base de Factory.

## Salida Esperada

Un diccionario con `ok`, `message` o `error`, y `data` con el plan o resultado.
