# Seguridad — factory3

## Regla de oro: nunca secrets en git

**Antes de cualquier commit:**
1. Verificar que `.gitignore` existe y cubre `.env`
2. Correr `git status` y confirmar que `.env` no aparece en staged
3. Nunca usar `git add .` o `git add -A` sin revisar primero

Si un `.env` llega a commitearse — aunque se corrija después — las credenciales están **comprometidas permanentemente** en el historial. GitHub lo detecta y bloquea futuros pushes.

---

## Archivos que NUNCA van a git

```
.env
*.env
.env.local
.env.production
secrets.*
*.key
*.pem
```

Todos deben estar en `.gitignore`. El repo ya tiene `.gitignore` en `main` — hacer pull antes del primer commit en cualquier rama nueva.

---

## Variables de entorno requeridas

Estas van solo en `.env` local y en las variables de entorno de Render. Nunca hardcodeadas en código.

### Core
| Variable | Descripción |
|---|---|
| `ANTHROPIC_API_KEY` | API key de Anthropic (claude-haiku / sonnet) |
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_KEY` | Anon key (acceso público limitado) |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (acceso total — solo backend) |
| `SUPABASE_DB_PASSWORD` | Password del proyecto Supabase |
| `SUPABASE_ACCESS_TOKEN` | Personal Access Token para Management API |
| `SUPABASE_PROJECT_REF` | Referencia del proyecto (ej: abcdefgh) |

### GitHub
| Variable | Descripción |
|---|---|
| `GITHUB_TOKEN` | Personal Access Token con permisos repo + workflow |
| `GITHUB_REPO` | Formato: `owner/repo` |
| `GITHUB_BRANCH` | Rama de deploy (normalmente `main`) |

### Render
| Variable | Descripción |
|---|---|
| `RENDER_API_KEY` | API key de Render |
| `RENDER_OWNER_ID` | Team/Owner ID de Render |

### Telegram
| Variable | Descripción |
|---|---|
| `TELEGRAM_TOKEN` | Token del bot admin (factory3_admin) |
| `MANAGER_CHAT_ID` | Chat ID del manager para alertas |

### Verticales
| Variable | Descripción |
|---|---|
| `RH_EMPRESA_ID` | ID de empresa activa para vertical RH |
| `DASHBOARD_URL` | URL del dashboard Streamlit (ej: https://factory3-dashboard.onrender.com) |
| `META_APP_ID` / `META_APP_SECRET` | Credenciales de Meta para vertical Instagram |

---

## Rotar credenciales comprometidas

Si una credencial llega al historial de git, rotarla inmediatamente:

- **ANTHROPIC_API_KEY** → console.anthropic.com → API Keys → revocar y crear nueva
- **SUPABASE keys** → dashboard.supabase.com → Settings → API → regenerar
- **SUPABASE_ACCESS_TOKEN** → supabase.com → Account → Access Tokens → revocar
- **GITHUB_TOKEN** → github.com → Settings → Developer settings → Personal access tokens → revocar
- **RENDER_API_KEY** → dashboard.render.com → Account Settings → API Keys → revocar

Después de rotar: actualizar `.env` local y variables en Render.

---

## Regla: todo lo nuevo sigue el patrón genérico

Cualquier cosa que se agregue a la fábrica debe seguir estas reglas:

1. **Skills** — toda lógica va en un skill (`skill.py` + `service.py`). Nunca lógica inline en bot.py o factory_api.py.
2. **Bot genérico** — `bot.py` ya es genérico: lee modos desde `_MODES` dict y delega a skills. Al agregar una vertical nueva, solo se agrega una entrada al dict.
3. **Datos como skills** — toda consulta a Supabase que use el bot O el dashboard va como skill de datos (`rh_stats`, `rh_list_vacantes`, etc.) expuesto vía `GET /data/{skill_name}` en `factory_api.py`.
4. **Dashboard genérico** — `dashboard/app.py` ya tiene estructura base genérica. Al agregar una vertical, se agrega una página que consume `/data/{skill}`.
5. **Doble ID** — toda tabla nueva tiene `id` UUID (interno) + `folio` visible (VAC-001, CAND-001).

### Pendiente: skills de datos + endpoint genérico

Lo siguiente en construir (vertical_rh en curso):

- [ ] Skill `rh_stats` — KPIs: total vacantes, candidatos, score promedio, seeds
- [ ] Skill `rh_list_vacantes` — lista filtrable de vacantes con folio
- [ ] Skill `rh_pipeline_view` — candidatos agrupados por etapa
- [ ] `GET /data/{skill_name}` en `factory_api.py` — endpoint genérico que invoca cualquier skill de datos

Una vez listos, el dashboard y el bot consumen los mismos skills. Sin lógica de DB duplicada.

### Pendiente (después de vertical_rh estable): mejoras en `new_factory`

- [ ] Crear servicio Render del dashboard además del API
- [ ] Copiar carpeta `dashboard/` al crear fábrica nueva
- [ ] Agregar `"vertical_rh": ["RH_EMPRESA_ID", "DASHBOARD_URL"]` a `VERTICAL_ENV_VARS`
- [ ] Correr migrations SQL de verticales al crear fábrica
- [ ] Crear `factory/skills/externos/.gitkeep` automáticamente

---

## Skills para crear una nueva fábrica

Este es el flujo completo para crear factory4 (o cualquier nueva fábrica) usando factory3 como base.

### Paso 1 — Infraestructura base
| Skill | Qué hace |
|---|---|
| `new_factory_github` | Crea el repo en GitHub con estructura base |
| `new_factory_supabase` | Crea proyecto Supabase y tablas base |
| `new_factory_render` | Crea servicio en Render y conecta con GitHub |
| `new_factory_telegram` | Crea/configura bot de Telegram y registra webhook |

### Paso 2 — Configuración
| Skill | Qué hace |
|---|---|
| `connect_supabase` | Conecta el engine al proyecto Supabase |
| `new_factory_cloud` / `new_factory_cloud_v2` | Configuración cloud completa (Render + Supabase + GitHub en un solo flujo) |
| `add_bot` | Registra un bot en `factory/bots/registry.json` |
| `connect_bot_agent` | Conecta bot con agente por defecto |

### Paso 3 — Verticales a copiar desde factory3
Copiar la carpeta completa de cada vertical que se necesite:

```
factory/skills/internos/rh_*/          → vertical RH completa (19 skills)
factory/skills/internos/bot_*/         → skills de bot multicanal
factory/skills/internos/ig_*/          → vertical Instagram
factory/skills/internos/meta_*/        → auth y conexión Meta
factory/skills/internos/supabase_*/    → operaciones Supabase
factory/skills/internos/github_*/      → operaciones GitHub
factory/skills/internos/render_*/      → operaciones Render
```

Usar `export_skill_pack` para empaquetar verticales y `add_skill` para importarlas en la nueva fábrica.

### Paso 4 — Tablas Supabase requeridas por vertical

**Vertical RH** (10 tablas):
```
vacantes, cuestionarios, candidatos, conversaciones,
respuestas, scores, pipeline, eventos_historial,
alertas, test_seeds
```
Crear con `supabase_sql_execute` usando los scripts de [VERTICAL_RH.md](VERTICAL_RH.md).

**Vertical Bot** (incluidas en RH):
- `conversaciones`, `candidatos` — ya cubiertas arriba

### Paso 5 — Variables de entorno en Render
Configurar todas las variables de la sección anterior usando `render_set_env_vars` o desde el dashboard de Render directamente.

---

## Estándar doble ID (obligatorio en todas las tablas)

A partir de esta versión, **toda tabla nueva debe tener**:

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID DEFAULT gen_random_uuid() | Interno — usado en JOINs, nunca se muestra al usuario |
| `folio` | TEXT UNIQUE | Visible al usuario — usado en comandos (VAC-001, CAND-001) |

El `folio` se genera automáticamente con una PostgreSQL sequence y un BEFORE INSERT trigger.

Ejemplo de migración:
```sql
CREATE SEQUENCE IF NOT EXISTS mi_tabla_folio_seq START 1;
ALTER TABLE mi_tabla ADD COLUMN IF NOT EXISTS folio TEXT;
CREATE OR REPLACE FUNCTION set_mi_tabla_folio() RETURNS TRIGGER AS $$
BEGIN
  NEW.folio := 'PRE-' || LPAD(nextval('mi_tabla_folio_seq')::TEXT, 3, '0');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mi_tabla_folio
  BEFORE INSERT ON mi_tabla FOR EACH ROW
  WHEN (NEW.folio IS NULL)
  EXECUTE FUNCTION set_mi_tabla_folio();
```

Prefijos en uso:
- `VAC-` → vacantes
- `CAND-` → candidatos

---

## Checklist antes de primer deploy

- [ ] `.gitignore` en el repo cubre `.env`
- [ ] Todas las credenciales en `.env` local (nunca en código)
- [ ] Variables de entorno configuradas en Render
- [ ] Webhook de Telegram apuntando a `https://<servicio>.onrender.com/webhook/factory3_admin`
- [ ] `MANAGER_CHAT_ID` configurado para recibir alertas
- [ ] `RH_EMPRESA_ID` configurado si se usa vertical RH
- [ ] `DASHBOARD_URL` configurado una vez creado el servicio del dashboard en Render
- [ ] Primer deploy manual disparado y verificado con `/health`
