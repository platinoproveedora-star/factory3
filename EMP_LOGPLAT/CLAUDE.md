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

## Skills planeados
| Skill | Descripción |
|---|---|
| `supabase_schema_create` | Crea schema en Supabase vía SQL (genérico) |
| `emp_logplat_viaje_registrar` | Registra viaje en `logplat.viajes` |
| `emp_logplat_gasto_registrar` | Registra gasto en `logplat.gastos` |
| `emp_logplat_reporte_gastos` | Resumen gastos por período/chofer |
| `emp_logplat_reporte_viajes` | Resumen viajes por período/chofer |

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
