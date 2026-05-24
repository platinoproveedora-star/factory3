"""Registra el webhook del bot Estoiko Lab en Telegram. Ejecutar una sola vez."""
import json
import os
import urllib.request
from pathlib import Path


def load_env():
    env = Path(__file__).parent / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() not in os.environ:
            os.environ[k.strip()] = v.strip().strip('"').strip("'")


load_env()

token       = os.getenv("ESTOIKOLAB_BOT_TOKEN", "")
factory_url = os.getenv("FACTORY_URL", "https://factory3.onrender.com")
webhook_url = f"{factory_url}/webhook/estoikolab_bot"

if not token:
    print("ERROR: ESTOIKOLAB_BOT_TOKEN no encontrado en .env")
    exit(1)

print(f"Token:   {token[:10]}...")
print(f"Webhook: {webhook_url}")
print("Registrando...")

payload = json.dumps({"url": webhook_url}).encode()
req = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/setWebhook",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req, timeout=15) as r:
    resp = json.loads(r.read().decode())
    if resp.get("ok"):
        print(f"✅ Webhook registrado: {webhook_url}")
    else:
        print(f"❌ Error: {resp}")
