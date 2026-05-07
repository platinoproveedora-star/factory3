# factory3

Runtime de skills, agentes y bots construido sobre FastAPI. Cada vertical de negocio se implementa como un conjunto de skills orquestados por un bot de Telegram.

## Arrancar localmente

```bash
uvicorn factory_api:app --reload --port 8000
```

Variables de entorno requeridas en `.env` — ver [docs/SEGURIDAD.md](docs/SEGURIDAD.md).

## Arquitectura

```
factory3/
├── factory_api.py          # FastAPI: webhook /webhook/{bot_name}, /health
├── factory/
│   ├── engine/             # Runtime core
│   │   ├── skill_loader.py
│   │   ├── skill_runner.py
│   │   ├── supabase_client.py
│   │   └── ...
│   ├── skills/
│   │   ├── registry.json   # Índice de todos los skills
│   │   └── internos/       # Un directorio por skill
│   │       └── <skill>/
│   │           ├── skill.py       # Entrypoint: run(context) -> dict
│   │           ├── service.py     # Lógica: Service.ejecutar(context)
│   │           └── manifest.json
│   ├── bots/
│   │   ├── registry.json   # Índice de bots (token_env, path)
│   │   └── factory3_admin/
│   │       └── bot.py      # handle_update(update, state) -> dict
│   └── agents/
│       └── registry.json
└── docs/                   # Documentación de verticales y seguridad
```

### Patrón de un skill

Todo skill recibe un `context: dict` y devuelve `{"ok": bool, "data": ..., "error": ...}`.

```python
# skill.py
def run(context: dict) -> dict:
    return MiService().ejecutar(context)

# service.py
class MiService:
    def ejecutar(self, context: dict) -> dict:
        db = SupabaseClient(context)
        ...
        return {"ok": True, "data": resultado}
```

### Patrón del bot (modal)

El bot es genérico. Cada modo (`/rh_1`, etc.) delega toda su lógica a un skill orquestador `{modo}_run`.

```
Telegram → /webhook/factory3_admin
  → bot.py handle_update(update, state)
    → si state["mode"]: runner.run("{mode}_run", {update, state})
    → si /rh_1: state["mode"] = "rh_1"
    → si /salir: state = {}
```

### Supabase

`SupabaseClient(context)` expone:
- `rest_select(tabla, filters, select, limit)`
- `rest_insert(tabla, values)`
- `rest_update(tabla, values, filters)`
- `rest_delete(tabla, filters)`
- `management_query(sql)` — DDL vía Management API

## Verticales activas

| Vertical | Modo bot | Docs |
|---|---|---|
| Recursos Humanos | `/rh_1` | [docs/VERTICAL_RH.md](docs/VERTICAL_RH.md) |
| Instagram / Meta | — | [docs/VERTICAL_IG.md](docs/VERTICAL_IG.md) |
| Bot multicanal | — | [docs/VERTICAL_BOT.md](docs/VERTICAL_BOT.md) |

## Verificar estructura antes de push

Después de cambios grandes, corre el verificador de salud local:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\venv\Scripts\python.exe main.py run-skill verify_factory --context-file ctx.json
```

Checa 8 puntos: compilación de skills, registry, carga de skills ejecutables, generadores, agente brain, bot routing. Si sale `ok: true` con 0 failures, la estructura está bien y es seguro hacer push.

## Deploy

Render auto-deploy en push a `main`. Servicio: `https://factory3.onrender.com`

Para crear una nueva fábrica desde esta ver [docs/SEGURIDAD.md → Skills new_factory](docs/SEGURIDAD.md).
