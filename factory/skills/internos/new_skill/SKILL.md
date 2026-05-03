---
name: new_skill
description: Crea la estructura base de un skill portable compatible con Factory.
version: "0.1.0"
type: internal
entrypoint: skill.py
contract: run(context) -> dict
permissions:
  filesystem: workspace-write
dependencies: []
mcps: []
---

## Rol

Crear skills portables con el estandar de Factory.

## Entrada Esperada

Un diccionario `context` con los datos necesarios para crear un skill.

## Salida Esperada

Un diccionario con `ok`, `message` o `error`, y `data` opcional.

## Estado

Esqueleto inicial. La logica de creacion todavia no esta implementada.

