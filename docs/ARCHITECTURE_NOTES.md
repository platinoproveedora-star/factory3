# Architecture Notes

Notas de arquitectura para decisiones futuras de factory3. Este documento guarda deuda, criterios y recomendaciones para no mezclar decisiones estructurales con el trabajo diario de verticales.

## Decision: no mover skills viejos todavia

Los skills existentes se quedan en su ubicacion actual. Moverlos ahora tiene riesgo alto de romper:

- llamadas existentes por nombre plano, como `rh_*`, `ig_*` o `meta_*`
- bots modales que esperan `<modo>_run`
- dashboards que consumen `GET /data/{skill}`
- entradas `kind=data` en `factory/skills/registry.json`
- paths ya usados por `SkillLoader`

## Decision: ordenar skills nuevos por vertical

Para trabajo nuevo, usar carpetas agrupadas por vertical dentro de `internos` mientras el runtime siga usando `skills/internos` como raiz principal:

```text
factory/skills/internos/vertical_marketing/<skill>/
factory/skills/internos/vertical_ads/<skill>/
factory/skills/internos/vertical_meta_ads/<skill>/
```

En `registry.json`, el `path` debe apuntar a la carpeta real. Si el nombre registrado usa slash, ejemplo `vertical_marketing/marketing_campaign_planner`, verificar que los runners que lo llamen usen exactamente ese nombre.

## Decision: empresas futuras

A partir de la siguiente empresa, crear una carpeta raiz ordenada:

```text
empresas/<CODIGO>/
```

En vez de seguir agregando nuevas carpetas `EMP_<CODIGO>/` en la raiz. Las empresas viejas no se mueven por ahora.

## Deuda LOGPLAT dashboard

- `EMP_LOGPLAT/dashboard/app.py` conecta directo a Supabase via `db.py` (con `SUPABASE_KEY` en env).
- La arquitectura correcta sería consumir `/data/emp_logplat_kpis` y `POST /run/<skill>` para escrituras.
- Pendiente: crear skills de escritura (crear/editar viaje, gasto, pago) y reescribir `db.py` para usar factory API.
- No se migra ahora por riesgo de romper CRUD del dashboard en producción.

## Deuda raiz factory3

- Revisar archivo raro `CUsersalfieCorfactory3requirements.txt`; parece salida accidental de una ruta mal escrita.
- `.gitignore` ya cubre `.env`, `venv/`, `.venv/`, `tmp/`, `*.pyc` y `__pycache__/`.
- `.codex/settings.local.json` ya quedo agregado a `.gitignore` para simetria con `.claude/settings.local.json`.
- Mantener `.claude/` y `.codex/` como configuracion de asistentes.
- No reordenar `EMP_*` viejos todavia.

## Deuda registry

- El registry central esta creciendo mucho y mezcla skills planos con algunos agrupados por ruta.
- Antes de mover skills viejos, crear aliases o una estrategia de compatibilidad.
- Revisar periodicamente entradas con `kind=data`, porque cambiar nombres rompe dashboards.
- Mantener `manifest.json`, `skill.py`, `service.py` y entrada en registry como contrato minimo.

## Deuda docs

- `docs/TABLES.md` debe registrar tablas nuevas con `id`, `empresa_id`, `usuario_id` cuando aplique, `created_at` y `updated_at`.
- Cada vertical nueva debe tener `docs/VERTICAL_<NOMBRE>.md`.
- `docs/WORK_LOG.md` queda para bitacora diaria; este archivo queda para decisiones estructurales.

## Decision: factory_users como tabla global de usuarios (2026-05-15)

`public.factory_users` es el registro centralizado de usuarios para todos los canales.
- WhatsApp: el `phone` registrado en `factory_users` determina el acceso y los modos
- Telegram: `telegram_id` se puede ligar al mismo usuario en el futuro
- Cada usuario tiene `user_mode text[]` — array de verticales permitidas
- El registro es auto-servicio vía `wabiz_access_codes`: usuario escribe código → nombre → queda registrado

No crear tablas de usuarios por canal (no `telegram_users`, no `wabiz_users`).
Todo va a `factory_users` con los campos de canal correspondientes (phone, telegram_id).

## Decision: router WhatsApp modal por usuario (2026-05-15)

El `wabiz_channel_router` no rutea por empresa_id en la URL.
Rutea por `factory_users.user_mode` del número que escribe:
- 1 modo → entra directo sin preguntar
- N modos → muestra menú, recuerda selección en bot_states

Los handlers son skills independientes en `factory/skills/internos/`:
- `emp_logplat_message_handler` para logplat
- Futuros: `emp_rh_message_handler`, etc.

Se agregan en `_MODO_HANDLERS` dict del router. Sin hard-code en factory_api.py.

## Revision rapida 2026-05-12

- Bot registry: existe `factory3_admin` como unico bot registrado.
- Agents registry: vacio por ahora.
- Skills registry: no se detectaron paths rotos en la revision rapida.
- Raiz: `venv/`, `tmp/`, `.env` y `.codex/settings.local.json` estan ignorados; queda pendiente el archivo raro de requirements.
