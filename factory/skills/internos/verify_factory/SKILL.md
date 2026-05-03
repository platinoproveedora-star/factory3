---
name: verify_factory
description: Verifica localmente la salud de Factory y sus unidades portables.
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

Ejecutar verificaciones locales repetibles de Factory sin depender de red ni tokens reales.

## Entrada Esperada

Un diccionario `context` opcional con:

- `base_dir`: ruta del repo o de la fabrica; por defecto se detecta desde el skill.
- `verbose`: booleano para incluir trazas de errores.

## Salida Esperada

Un diccionario con `ok`, `message` y `data.checks`.
