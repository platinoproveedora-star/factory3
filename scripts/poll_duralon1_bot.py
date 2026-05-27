from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factory_api import load_env_file, process_bot_update, telegram_request


BOT_NAME = "duralon1_bot"
TOKEN_ENV = "UC101_PROY001_BOT_TOKEN"


def _telegram_get_updates(token: str, offset: int | None) -> list[dict]:
    params = {"timeout": 25, "allowed_updates": json.dumps(["message", "callback_query"])}
    if offset is not None:
        params["offset"] = offset
    url = f"https://api.telegram.org/bot{token}/getUpdates?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=35) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(payload)
    return payload.get("result") or []


def main() -> None:
    load_env_file()
    token = os.getenv(TOKEN_ENV)
    if not token:
        raise SystemExit(f"{TOKEN_ENV} no configurada")

    telegram_request(token, "deleteWebhook", {"drop_pending_updates": False})
    print(f"Polling activo para {BOT_NAME}. Ctrl+C para detener.")
    offset: int | None = None

    while True:
        try:
            updates = _telegram_get_updates(token, offset)
            for item in updates:
                update_id = item.get("update_id")
                if isinstance(update_id, int):
                    offset = update_id + 1
                result = process_bot_update(BOT_NAME, item)
                print(json.dumps({"update_id": update_id, **result}, ensure_ascii=False))
        except KeyboardInterrupt:
            print("Polling detenido.")
            return
        except Exception as exc:
            print(f"Error polling: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    main()
