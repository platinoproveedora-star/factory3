"""Limpia estados corruptos en bot_states (modo 'rh1' obsoleto)."""
import os, sys, json
from pathlib import Path

for line in (Path(__file__).parent.parent / ".env").read_text(encoding="utf-8").splitlines():
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in raw:
        continue
    k, v = raw.split("=", 1)
    k = k.strip(); v = v.strip().strip('"').strip("'")
    if k and k not in os.environ:
        os.environ[k] = v

sys.path.insert(0, str(Path(__file__).parent.parent))
from factory.engine import SupabaseClient

db = SupabaseClient({})

# Listar todos los estados actuales
print("=== Estados actuales ===")
r = db.rest_select("bot_states", select="*")
rows = r.get("data") or []
for row in rows:
    print(f"  chat_id={row.get('chat_id')}  state={row.get('state')}")

# Limpiar cualquier estado con modo inválido (rh1 ya no existe, se llama rh_1)
fixed = 0
for row in rows:
    state = row.get("state") or {}
    mode = state.get("mode", "")
    if mode == "rh1":
        chat_id = row["chat_id"]
        result = db.rest_update(
            "bot_states",
            values={"state": {}},
            filters={"chat_id": str(chat_id)},
        )
        if result.get("ok"):
            print(f"  [OK] Limpiado chat_id={chat_id} (modo 'rh1' → {{}})")
            fixed += 1
        else:
            print(f"  [ERR] chat_id={chat_id}: {result.get('error')}")

print(f"\nTotal corregidos: {fixed}")
