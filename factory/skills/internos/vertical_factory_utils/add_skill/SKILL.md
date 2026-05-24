---
name: add_skill
description: Importa skills externos portables a Factory
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

Importar skills externos portables a `factory/skills/externos` y registrarlos.

## Entrada Esperada

Un diccionario `context` con:

- `nombre`
- `path` para importacion local
- `url` para importar desde `.zip`, `file://` o repo git
- `descripcion`
- `vertical`
- `dry_run`
- `base_dir`

## Flujo

1. Resolver origen desde `path` o `url`.
2. Si viene de `url`, preparar cuarentena en `factory/workspace/imports/{nombre}`.
3. Detectar la raiz real del skill buscando `SKILL.md`, incluso si viene anidado.
4. Validar o generar `skill.py` como wrapper delgado cuando hay un unico script principal.
5. Copiar a `factory/skills/externos/{nombre}` cuando `dry_run` sea falso.
6. Registrar el skill en `factory/skills/registry.json`.

## Salida Esperada

Un diccionario con `ok`, `message` o `error`, y `data` con plan o resultado.
