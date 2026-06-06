# Factory3 — Claude Context

## ⚠️ STOP — Lee esto antes de tocar cualquier código

1. Revisa `factory/skills/registry.json` — si el skill existe, úsalo, no lo recrees
2. Revisa `factory/engine/` — no reimplementes SupabaseClient ni SkillRunner
3. Todo skill nuevo: `manifest.json` + `skill.py` + `service.py` — sin excepciones
4. Lee `docs/VERTICAL_<nombre>.md` del área en que vas a trabajar
5. No crees carpetas ni archivos fuera de la estructura establecida
6. No agregues dependencias sin agregarlas a `requirements.txt`
7. Si no encuentras el patrón aquí → **pregunta antes de inventar**

### Mapa de docs por tema
- Arquitectura general: `docs/FACTORY_ARCHITECTURE.md`, `docs/ARCHITECTURE_NOTES.md`
- Verticales: `docs/VERTICAL_<nombre>.md`
- Empresas: `companies/EMP_*/AGENTS_ARCHITECTURE.md`
- Clientes Upwork: `companies/EMP_FREELANCE_GROWTH/`
- Skills disponibles: `factory/skills/registry.json`

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

## QA Enterprise — skills de operación (vertical: qa)

Cinco skills reutilizables para operar campañas con seguridad:

| Skill | Función | Tablas Supabase |
| --- | --- | --- |
| `qa_secrets_check` | Verifica env vars por categoría (core, meta_ads, telegram, render, github) | ninguna |
| `qa_preflight` | Checklist antes de lanzar (landing, WhatsApp, privacidad, imagen, lead form, presupuesto, copy, approver, pixel, token Meta) | ninguna |
| `qa_campaign_logger` | Log estructurado empresa/campaña/skill con semáforo | `qa_execution_logs` |
| `qa_rollback_campaign` | Backup config campaña + pausa Meta + restore | `qa_campaign_backups` |
| `qa_skills_test` | Test runner automático de 6 skills críticos | ninguna |

### Uso típico antes de lanzar campaña

```python
# 1. Verificar secrets
run("qa_secrets_check", {"categories": ["core", "meta_ads"]})

# 2. Preflight completo
run("qa_preflight", {
    "company_id": "EMP_ABC", "campaign_id": "camp_001",
    "landing_url": "https://...", "privacy_url": "https://...",
    "whatsapp_link": "https://wa.me/521...", "image_url": "https://...",
    "lead_form_id": "120208...", "daily_budget": 200,
    "ad_copy": "Texto del anuncio...", "approver": "nombre_aprobador",
    "pixel_id": "PIXEL_ID", "campaign_status": "PAUSED",
})

# 3. Log ejecución
run("qa_campaign_logger", {
    "action": "log",
    "company_id": "EMP_ABC", "campaign_id": "camp_001",
    "skill_name": "meta_ads_publish_flow",
    "status": "ok", "message": "campaña publicada",
})

# 4. Si algo falla — rollback
run("qa_rollback_campaign", {
    "action": "backup_and_pause",
    "company_id": "EMP_ABC", "campaign_id": "120208...",
    "motivo": "error_en_deploy",
})
```

### Crear tablas Supabase (una vez por proyecto)

```python
run("qa_campaign_logger",  {"action": "ensure_table", "dry_run": False})
run("qa_rollback_campaign", {"action": "ensure_table", "dry_run": False})
```

### Reglas de modo seguro

- `qa_rollback_campaign` siempre crea backup ANTES de pausar
- `qa_preflight` bloquea lanzamiento si hay checks `fail` (no `warn`)
- `qa_secrets_check` nunca expone valores — solo longitud de cada var
- Campañas siempre se crean en `PAUSED` — `qa_preflight` lo verifica
- `qa_skills_test` usa `skip_url_checks=True` para tests sin red
## FACTORY3 SELLABLE GATE - OBLIGATORIO

Factory3 se construye para vender y reutilizar modulos por empresa. Antes de crear o modificar codigo, cualquier agente debe cumplir este gate:

1. Resolver contexto desde `companies/<EMPRESA>/projects/<PROY>/project.json` o `PROY-003_ERP_CORE/modules.json`.
2. Pasar siempre `company_id`/`empresa_id`, `project_code`, `module_code` y `schema` por `context`.
3. No hardcodear identidad vendible en codigo generico: `EMP_DURALON`, `UC-101`, schemas `uc101_*`, URLs fijas, nombres de empresa, prefijos o folios especificos.
4. Dashboards deben leer env/config y llamar Factory API/data skills; no deben guardar credenciales ni identidad fija.
5. La logica reusable vive en skills internos; la UI solo captura datos y llama endpoints/skills.
6. Si un modulo no puede copiarse a otra empresa cambiando config + schema + env vars, no esta listo para cierre.

Hardcodes permitidos solo si estan en `project.json`, `modules.json`, `render.yaml`, `.env.example`, docs, seeds especificos, o si son defaults de prueba claramente sobreescribibles por `context`/env.

Antes de cerrar o deployar un modulo ERP:

- Correr/revisar `vertical_erp/erp_health_check`.
- Buscar hardcodes de identidad: `EMP_`, `UC-`, `uc101_`, URLs Render/Vercel, schemas fijos.
- Si aparecen en codigo generico, corregirlos o documentar bloqueo.
- Confirmar que toda escritura reusable respeta `dry_run=True` por default.

Skills/gates requeridos para evitar repetir deuda:

- `vertical_erp/erp_project_context_resolve`: carga contexto estandar desde `project.json`, `modules.json`, env y overrides.
- `vertical_erp/erp_no_hardcode_audit`: escanea codigo para detectar identidad/schema/URLs fijas en zonas vendibles.
- `vertical_erp/erp_module_export_plan`: genera plan para copiar/vender un modulo a otra empresa.
- `vertical_dashboards/dashboard_context_adapter`: patron para dashboards que leen contexto sin hardcodes.
