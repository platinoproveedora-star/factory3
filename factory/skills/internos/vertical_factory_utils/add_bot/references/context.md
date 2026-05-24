# Contexto: add_bot

## Proposito

Crear bots Telegram independientes para Factory.

## Reglas

- No recibir tokens directos.
- Leer token solo por `token_env`.
- No escribir secretos en `config.json` ni registry.
- Generar bots portables con `bot.py` delgado y logica en `scripts/`.
- Registrar bots en `factory/bots/registry.json`.
