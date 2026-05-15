# LOGPLAT — Claude Context

## Empresa
- Platino Logística (`LOGPLAT`)
- Admin: Alfredo. Operadores: choferes en campo.
- Inicio: Mayo 2026

## Convención de nombres
```
EMP_LOGPLAT_<FUNCION>/   ← carpeta skill
emp_logplat_<funcion>    ← nombre en registry
```
Skills genéricos (sin empresa) no llevan prefijo `EMP_`.

## Stack
- Supabase — schema `logplat` (aislado de `public`)
- Runtime: factory3 (`factory_api.py` + skills)
- Captura: por definir

## Tablas

### `logplat.viajes`
`id` (uuid), `folio` (VIA-001…), `fecha`, `chofer`, `origen`, `destino`, `km`, `notas`, `created_at`

### `logplat.gastos`
`id` (uuid), `folio` (GAS-001…), `fecha`, `chofer`, `viaje_folio`, `concepto`, `monto`, `comprobante_url`, `notas`, `created_at`

## Estructura de código
```
EMP_LOGPLAT/
  CLAUDE.md
  EMP_LOGPLAT.md
  service.py          ← toda la lógica DB (viajes, gastos, pagos, cxp)
  bot_mode.py         ← handler modo /logplat del bot factory3_admin
```
Skills de reporte (si se necesitan) van en `factory/skills/internos/emp_logplat_*/` e importan `service.py` desde `EMP_LOGPLAT/`.

## Skills activos
| Skill | Canal | Descripción |
|---|---|---|
| `logplat_run` | Telegram | Orquestador bot /logplat — gastos, viajes, pagos, docs |
| `emp_logplat_kpis` | Dashboard | KPIs: utilidad semanal, CXC, viajes |
| `emp_logplat_message_handler` | WhatsApp | Handler canal-agnostic: gastos, viajes, docs |

## Canal WhatsApp

Integrado vía `vertical_wabiz`. El handler es **canal-agnostic** — recibe
`{type, body, media_id, from_phone}` y devuelve `{reply}`.
El router (`wabiz_channel_router`) gestiona registro, modal y envío.

Registro de usuarios:
- Código chofer: `logplat26` → acceso a modo logplat
- Código admin: `admin2026` → acceso a modo logplat

El nombre del chofer se toma de `factory_users.nombre` y se guarda automáticamente
en gastos y viajes.

Estado de sesión en `bot_states`:
- Router: `wabiz_{empresa_id}_{phone}` → `{active_mode, reg_step…}`
- Handler: `wabiz_logplat_{phone}` → `{hint, doc_url, doc_name}`

## Estado
- [ ] Crear schema `logplat` + tablas en Supabase
- [ ] `emp_logplat_viaje_registrar`
- [ ] `emp_logplat_gasto_registrar`
- [ ] Captura retroactiva mayo (3 viajes)
- [ ] Skills de reporte

## Orden de construcción
1. Schema + tablas (manual o `supabase_schema_create`)
2. `emp_logplat_viaje_registrar`
3. `emp_logplat_gasto_registrar`
4. Captura retroactiva
5. Skills de reporte

## Reglas de arquitectura
- Todo en `skill.py` + `service.py`. Nunca lógica inline en bot.py o factory_api.py.
- Doble ID en toda tabla: `id` (uuid) + `folio` visible.
- Skills `kind=data` para reportes, expuestos via `GET /data/{skill}`.
- Schema `logplat` aislado de `public`.
