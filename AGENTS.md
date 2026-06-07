# Factory3 — Codex Context

## ⚠️ STOP — Lee esto antes de tocar cualquier código

1. Revisa `factory/skills/registry.json` — si el skill existe, úsalo, no lo recrees
2. Revisa `factory/engine/` — no reimplementes SupabaseClient ni SkillRunner
3. Todo skill nuevo: `manifest.json` + `skill.py` + `service.py` — sin excepciones
4. Lee `docs/VERTICAL_<nombre>.md` del área en que vas a trabajar
5. No crees carpetas ni archivos fuera de la estructura establecida
6. No agregues dependencias sin agregarlas a `requirements.txt`
7. Si no encuentras el patrón aquí → **pregunta antes de inventar**

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
    skills/
      registry.json       ← registro de skills — LEER ANTES DE CREAR
      internos/           ← todos los skills
    engine/               ← SupabaseClient, SkillLoader, SkillRunner — NO reimplementar
  EMP_<CODIGO>/           ← código por empresa (service.py + bot_mode.py)
  docs/                   ← VERTICAL_*.md — leer antes de trabajar en un área
  companies/              ← configs y arquitectura por empresa
```

## Patrón obligatorio de un skill
```
<nombre>/
  manifest.json   ← OBLIGATORIO
  skill.py        ← def run(context: dict) -> dict
  service.py      ← lógica aquí, skill.py solo delega
```

### Retorno estándar
```python
{"ok": True,  "data": {...}}   # éxito
{"ok": False, "error": "..."}  # fallo
```

### dry_run
Skills con escritura respetan `context.get("dry_run", True)` — no escriben si es True.

## Anti-patrones — NO hacer
- No conectar Supabase directo — usar `factory/engine/SupabaseClient`
- No crear engine propio ni cliente HTTP propio para Supabase
- No hardcodear rutas absolutas
- No crear skills fuera de `factory/skills/internos/`
- No omitir `manifest.json` ni entrada en `registry.json`
- No crear tabla sin doble ID (`id uuid` + `folio text UNIQUE`)

## Mapa de docs por tema
- Arquitectura general: `docs/FACTORY_ARCHITECTURE.md`, `docs/ARCHITECTURE_NOTES.md`
- Verticales: `docs/VERTICAL_<nombre>.md`
- Empresas: `companies/EMP_*/AGENTS_ARCHITECTURE.md`
- Clientes Upwork: `companies/EMP_FREELANCE_GROWTH/`
- Skills disponibles: `factory/skills/registry.json`

## Supabase — reglas clave
- Schemas separados por empresa — usar headers `Accept-Profile` / `Content-Profile`
- Doble ID en toda tabla nueva: `id uuid PRIMARY KEY` + `folio text UNIQUE NOT NULL`
- Schema debe estar expuesto en Supabase Dashboard → Settings → Data API

## Env vars principales
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_ACCESS_TOKEN
ANTHROPIC_API_KEY
FACTORY3_ADMIN_BOT_TOKEN
GITHUB_REPO / GITHUB_TOKEN
RENDER_API_KEY
```

## Reglas de arquitectura
- Todo en `skill.py` + `service.py` — nunca lógica inline en `bot.py` o `factory_api.py`
- Skills `kind=data` para datos del dashboard, expuestos via `GET /data/<skill>`
- `dry_run=True` por defecto en skills con escritura
- User-Agent en requests externos: `"FactoryFactory/0.1 (+https://github.com/)"`
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

## GOBERNANZA UNIVERSAL ANTI-HARDCODING - OBLIGATORIO

Esta regla aplica a TODO Factory3: skills, bots, dashboards, scripts, seeders, APIs, agentes y cualquier vertical, no solo ERP.

Regla de oro: ningun codigo reusable puede hardcodear:

- `empresa_id` / `company_id`
- schemas Supabase (`uc101_*`, `logplat`, o cualquier schema de cliente)
- `project_code` / `module_code`
- URLs Render/Vercel o dominios de despliegue
- tokens, write keys, service keys o nombres parciales de secretos como valores

Todo debe venir de `context`, `project.json`, `company.json`, `modules.json`, env vars o config versionada especifica del proyecto. Si falta contexto, el codigo debe devolver error explicito. Prohibidos los fallbacks silenciosos a clientes reales.

### project.json minimo obligatorio

Todo proyecto en `companies/EMP_XXX/projects/PROY-XXX*/` debe tener `project.json` con minimo:

```json
{
  "company_id": "EMP_XXX",
  "project_code": "PROY-001",
  "module_code": "nombre_modulo",
  "schema": "schema_cliente",
  "platform": "render",
  "requires_env": ["SUPABASE_URL"]
}
```

Sin `project.json`, el proyecto no es valido para cierre, deploy o venta.

### Patron obligatorio de contexto en service.py

Todo `service.py` que necesite schema/empresa debe resolver contexto asi, o con `factory_project_context_resolve`:

```python
def _resolve_context(self, context: dict) -> dict:
    schema = str(context.get("schema") or context.get("supabase_schema") or "").strip()
    company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
    if not schema:
        return {"ok": False, "error": "schema requerido en context"}
    if not company_id:
        return {"ok": False, "error": "company_id requerido en context"}
    return {"ok": True, "data": {**context, "schema": schema, "company_id": company_id}}
```

### Skills universales de gobernanza

- `factory_project_context_resolve`: resolver contexto multiempresa desde `context`, `company.json`, `project.json` y `modules.json`.
- `factory_no_hardcode_audit`: auditar hardcodes en cualquier vertical/proyecto.
- `company_scaffold`: crear empresa/proyecto con estructura correcta desde el inicio.

Antes de cerrar cambios nuevos:

- Correr `factory_no_hardcode_audit` sobre los paths tocados.
- Confirmar `0 blockers`.
- Si quedan warnings, documentar si son env vars/config permitida o corregirlos.
