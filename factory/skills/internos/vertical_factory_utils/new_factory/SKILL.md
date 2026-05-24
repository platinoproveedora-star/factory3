# new_factory

Crea una fabrica generica desde la fabrica actual.

## Uso

Ejecuta `new_factory` con `factory_name`, `mode` (`local` o `cloud`) y, opcionalmente, `verticals`.

En modo `local`, genera carpetas y copia los skills registrados de las verticales seleccionadas.

En modo `cloud`, crea repo GitHub, servicio Render y configura webhook Telegram.

Opcionales utiles:

- `package_dir`: carpeta base del runtime generado. Default: `factory`.
- `source_package_dir`: carpeta base de la fabrica actual usada como fuente. Default: `factory`.
- `api_module`: modulo ASGI para Render. Default: `factory_api:app`.
- `admin_bot_token_env`: nombre env para token admin. Default: `ADMIN_BOT_TOKEN`.
- `admin_chat_id_env`: nombre env para chat admin. Default: `ADMIN_CHAT_ID`.
