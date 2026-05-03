---
name: security_gate
description: Gate de seguridad basico para revisar skills externos antes de instalarlos
version: "0.1.0"
type: internal
entrypoint: skill.py
contract: run(context) -> dict
vertical: security
permissions: []
dependencies: []
mcps: []
---

## Rol

Revisar skills externos en cuarentena antes de copiarlos a `factory/skills/externos`.

## Entrada Esperada

Un diccionario `context` con:

- `path`: carpeta del skill a revisar
- `strict`: opcional, si es `true` convierte `WARN` en bloqueo

## Salida Esperada

Un diccionario con:

- `ok`
- `verdict`: `PASS`, `WARN` o `FAIL`
- `summary`
- `findings`

## Alcance

Este gate hace analisis estatico basico. No ejecuta codigo del skill.
