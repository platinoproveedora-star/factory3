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
