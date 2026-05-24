def render(data: dict, telegram_bot: dict) -> str:
    commands = "\n".join(f"- /{command}" for command in data["commands"])
    return f"""# {data['bot_name']}

Bot Telegram generado por `add_bot`.

## Tipo

{data['bot_type']}

## Telegram

@{telegram_bot.get('username', '')}

## Token

El token se lee desde `{data['token_env']}`. No guardar el valor real en Git.

## Comandos

{commands}
"""
