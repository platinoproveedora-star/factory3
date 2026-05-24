def render(nombre: str, vertical: str, descripcion: str) -> str:
    return f"""---
name: {nombre}
description: {descripcion}
version: "0.1.0"
type: internal
entrypoint: skill.py
contract: run(context) -> dict
vertical: {vertical}
permissions: []
dependencies: []
mcps: []
---

## Rol

TODO: definir rol del skill.

## Entrada Esperada

TODO: definir entrada esperada.

## Salida Esperada

TODO: definir salida esperada.
"""
