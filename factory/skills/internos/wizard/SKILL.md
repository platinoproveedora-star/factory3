---
name: wizard
description: Maneja flujos conversacionales para bots de Factory
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

Guiar flujos conversacionales para crear recursos de Factory.

## Entrada Esperada

Un diccionario `context` con:

- `flow`: nombre del flujo; hoy soporta `new_agent`
- `text`: respuesta del usuario para el paso actual
- `state`: estado devuelto por el paso anterior

## Salida Esperada

Un diccionario con `ok`, `response`, `state` y `done`.

En el flujo `new_agent`, el wizard pregunta si el agente debe usar memoria Supabase
y pasa `memory: true/false` al contexto final de `new_agent`.
