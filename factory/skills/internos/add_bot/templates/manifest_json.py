import json


def render(data: dict, telegram_bot: dict) -> str:
    return json.dumps(
        {
            "type": "bot",
            "name": data["bot_name"],
            "version": "0.1.0",
            "kind": "executable",
            "entrypoint": "bot.py",
            "bot_type": data["bot_type"],
            "empresa": data["empresa"],
            "token_env": data["token_env"],
            "telegram_username": telegram_bot.get("username", ""),
            "commands": data["commands"],
            "permissions": ["telegram:send_message"],
            "requires_env": [data["token_env"]],
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n"
