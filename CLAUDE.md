# Factory3 — Claude Context

## Qué es factory3
Runtime de skills Python. Expone bots Telegram y endpoints HTTP via FastAPI (`factory_api.py`).
Todo corre en Render. DB: Supabase. IA: Anthropic Haiku.

## Estructura raíz
```
factory3/
  factory_api.py          ← FastAPI: webhooks + GET /data/{skill}
  factory/
    bots/
      registry.json       ← registro de bots
      factory3_admin/
        bot.py            ← dispatcher modal genérico
    skills/
      registry.json       ← registro de skills
      internos/           ← todos los skills
    engine/               ← SkillLoader, SkillRunner, SupabaseClient
  EMP_<CODIGO>/           ← código por empresa (service.py + bot_mode.py)
  docs/
```

## Regla crítica: estructura de un skill

**Todo skill en `factory/skills/internos/<nombre>/` NECESITA obligatoriamente:**

```
<nombre>/
  manifest.json   ← OBLIGATORIO — sin esto SkillLoader lanza FileNotFoundError
  skill.py        ← OBLIGATORIO — entrypoint: def run(context: dict) -> dict
  service.py      ← convención fuerte (lógica aquí, skill.py solo delega)
```

### manifest.json mínimo
```json
{
  "type": "skill",
  "name": "<nombre>",
  "version": "0.1.0",
  "kind": "executable",
  "entrypoint": "skill.py",
  "description": "...",
  "requires_env": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
}
```

### skill.py patrón estándar
```python
from __future__ import annotations
from service import MiService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return MiService().ejecutar(context)
```

### Retorno estándar
```python
{"ok": True,  "data": {...}}   # éxito
{"ok": False, "error": "..."}  # fallo
```

### dry_run
Todos los skills con escritura deben respetar `context.get("dry_run", True)` — no escriben nada si es True.

## Skills kind=data

Para exponer datos al dashboard via `GET /data/<nombre>`:
- Agregar `"kind": "data"` en `manifest.json` Y en `registry.json`
- El endpoint recibe query params como context
- Retorna `{"ok": True, "data": {...}}`

## registry.json de skills

Cada skill nuevo debe agregarse a `factory/skills/registry.json`:
```json
"<nombre>": {
  "tipo": "interno",
  "nombre": "<nombre>",
  "vertical": "<vertical>",
  "kind": "data",          ← solo si es kind=data
  "descripcion": "...",
  "path": "skills/internos/<nombre>",
  "entrypoint": "skill.py",
  "version": "0.1.0"
}
```

## Bots — modo modal

`factory/bots/factory3_admin/bot.py` usa `_MODES` dict:
```python
_MODES = {
    "/rh1":     "rh_1",
    "/logplat": "logplat",
}
```

Cada modo delega a `<modo>_run` skill via SkillRunner.
El estado de modo se persiste en `bot_states` (Supabase, schema public).

### Agregar un modo nuevo requiere:
1. Entrada en `_MODES` en `bot.py`
2. Skill `<modo>_run/` con su `manifest.json`
3. Botón en el markup de `/ayuda`

## Empresas (EMP_*)

Cada empresa vive en `EMP_<CODIGO>/`:
```
EMP_<CODIGO>/
  CLAUDE.md       ← contexto específico de la empresa
  service.py      ← CRUD + lógica negocio (NO importar en bot.py ni factory_api)
  bot_mode.py     ← handler del bot
```

El skill `<codigo>_run/skill.py` en `factory/skills/internos/` actúa como bridge:
```python
_DIR = Path(__file__).parent.parent.parent.parent.parent / "EMP_<CODIGO>"
sys.path.insert(0, str(_DIR))
import bot_mode
```

## Supabase

### Schemas separados por empresa
Cada empresa usa su propio schema PostgreSQL (ej. `logplat`).
Para acceder via REST se necesita:
- `Accept-Profile: <schema>` en GET
- `Content-Profile: <schema>` + `Prefer: return=representation` en POST/PATCH/DELETE
- El schema debe estar expuesto en Supabase: **Dashboard → Settings → Data API → Exposed schemas**

### SupabaseClient (engine)
```python
from factory.engine import SupabaseClient
db = SupabaseClient(context)
db.rest_select(table, filters={}, select="*", limit=None, order=None)
db.rest_insert(table, rows)
db.rest_update(table, values, filters)
db.rest_delete(table, filters)
db.management_query(sql)   ← Management API (requiere SUPABASE_ACCESS_TOKEN)
```

`_VALID_NAME` en los skills CRUD solo acepta `^[a-z][a-z0-9_]*$` — no soporta `schema.tabla`.
Para schemas no-public, hacer requests directos con headers de schema.

### Doble ID en toda tabla nueva
```sql
id    uuid PRIMARY KEY DEFAULT gen_random_uuid()   ← interno
folio text UNIQUE NOT NULL                          ← visible (VIA-001, GAS-001)
```

## Anthropic / Haiku

```python
import urllib.request, json, os

payload = {
    "model":      "claude-haiku-4-5-20251001",
    "max_tokens": 1024,
    "messages":   [{"role": "user", "content": "..."}],
}
req = urllib.request.Request(
    "https://api.anthropic.com/v1/messages",
    data=json.dumps(payload).encode(),
    headers={
        "content-type":      "application/json",
        "x-api-key":         os.getenv("ANTHROPIC_API_KEY"),
        "anthropic-version": "2023-06-01",
        "anthropic-beta":    "pdfs-2024-09-25",  ← solo si usas PDFs
    },
    method="POST",
)
```

Para imágenes: content es lista con `{"type": "image", "source": {"type": "base64", ...}}`.
Para PDFs: `{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", ...}}`.

## Env vars principales

```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_ACCESS_TOKEN       ← Management API (crear tablas via SQL)
SUPABASE_PROJECT_REF        ← o se deriva de SUPABASE_URL
ANTHROPIC_API_KEY
FACTORY3_ADMIN_BOT_TOKEN    ← bot admin Telegram
GITHUB_REPO / GITHUB_TOKEN  ← para skills que pushean
RENDER_API_KEY              ← para skills que crean servicios
```

## Reglas de arquitectura

- Todo en `skill.py` + `service.py`. Nunca lógica inline en `bot.py` o `factory_api.py`
- Bot genérico: `_MODES` dict, sin hard-code por vertical
- Skills `kind=data` para datos del dashboard, expuestos via `GET /data/<skill>`
- Dashboard consume `/data/` via HTTP, no credenciales Supabase directas
- Doble ID en toda tabla nueva
- `dry_run=True` por defecto en skills con escritura
- User-Agent en requests a APIs externas (Cloudflare bloquea sin él): `"FactoryFactory/0.1 (+https://github.com/)"`
- Estado bot atorado: limpiar en `bot_states` donde `state->>'mode' = '<modo>'`

## Checklist al crear un skill nuevo

- [ ] `manifest.json` con `name`, `kind`, `entrypoint`, `description`, `requires_env`
- [ ] `skill.py` con `def run(context: dict) -> dict`
- [ ] `service.py` con la lógica
- [ ] Entrada en `factory/skills/registry.json`
- [ ] Si es bot mode: entrada en `_MODES` + botón en `/ayuda` + skill `<modo>_run`
