---
name: add_bot
description: Crea bots Telegram configurables para Factory
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

Crear bots Telegram configurables para Factory sin guardar secretos en codigo ni registry.

## Entrada Esperada

Un diccionario `context` con:

- `bot_name`: nombre interno en snake_case
- `bot_type`: `admin`, `client` o `internal`
- `token_env`: nombre de la variable de entorno con el token
- `admin_chat_id`: chat id autorizado para recibir prueba
- `empresa`: empresa o proyecto dueño
- `commands`: comandos iniciales
- `dry_run`: si es `true`, no escribe archivos ni llama Telegram
- `base_dir`: carpeta base de Factory

## Salida Esperada

Un diccionario con `ok`, `message` o `error`, y `data` con plan o resultado.
