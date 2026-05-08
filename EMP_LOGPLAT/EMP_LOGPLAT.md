# Logística Platino — Proyecto

## Contexto
- Empresa: Platino Logística
- Código empresa: `LOGPLAT`
- Admin: Alfredo (solo, maneja todo lo administrativo)
- Operadores: choferes en campo
- Mes de inicio: Mayo 2026 (3 viajes ya registrados pendientes)

## Convención de nombres (archivos, skills, tablas)
```
EMP_LOGPLAT_<FUNCION>.py / .md
emp_logplat_<funcion>          ← nombre de skill en registry
```
Escalable a otras empresas: `EMP_TRANSNORTE_*`, `EMP_DISTMEX_*`, etc.
Skills 100% genéricos (sin empresa) no llevan prefijo `EMP_`: ej. `supabase_schema_create`.

## Filosofía de construcción
Cada funcionalidad genera **skills genéricos reutilizables** cuando aplica, y skills `emp_logplat_*` para lógica específica del cliente. Ambos viven en `factory/skills/internos/`.

## Stack elegido
- **Almacenamiento:** Supabase (mismo proyecto factory3, schema separado `logplat`)
- **Captura:** por definir (Telegram bot, form web, o entrada manual)
- **Runtime:** factory3 (`factory_api.py` + skills)

## Supabase — Schema `logplat`
Separación por schema de PostgreSQL: cada empresa tiene su propio schema.
Las tablas de este cliente viven en `logplat.*` y no se mezclan con `public.*` (RH, etc.).

### Tabla: `logplat.viajes`
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK interno |
| folio | text | VIA-001, VIA-002... |
| fecha | date | |
| chofer | text | |
| origen | text | |
| destino | text | |
| km | numeric | opcional |
| notas | text | |
| created_at | timestamptz | |

### Tabla: `logplat.gastos`
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK interno |
| folio | text | GAS-001, GAS-002... |
| fecha | date | |
| chofer | text | |
| viaje_folio | text | FK a viajes.folio (opcional) |
| concepto | text | combustible, caseta, alimento, etc. |
| monto | numeric | MXN |
| comprobante_url | text | opcional |
| notas | text | |
| created_at | timestamptz | |

## Skills a construir

### Genéricos (reutilizables)
| Skill | Descripción |
|---|---|
| `supabase_schema_create` | Crea un schema en Supabase vía SQL |

### Empresa LOGPLAT
| Skill | Archivo | Descripción |
|---|---|---|
| `emp_logplat_viaje_registrar` | `EMP_LOGPLAT_VIAJE_REGISTRAR/` | Registra viaje en `logplat.viajes` |
| `emp_logplat_gasto_registrar` | `EMP_LOGPLAT_GASTO_REGISTRAR/` | Registra gasto en `logplat.gastos` |
| `emp_logplat_reporte_gastos` | `EMP_LOGPLAT_REPORTE_GASTOS/` | Resumen gastos por período/chofer |
| `emp_logplat_reporte_viajes` | `EMP_LOGPLAT_REPORTE_VIAJES/` | Resumen viajes por período/chofer |

## Estado actual
- [ ] Crear schema `logplat` en Supabase
- [ ] Crear tablas `logplat.viajes` y `logplat.gastos`
- [ ] Skill `emp_logplat_viaje_registrar`
- [ ] Skill `emp_logplat_gasto_registrar`
- [ ] Captura retroactiva mayo (3 viajes pendientes)
- [ ] Skills de reporte

## Orden de construcción
1. Schema + tablas en Supabase (manual o skill genérico)
2. `emp_logplat_viaje_registrar`
3. `emp_logplat_gasto_registrar`
4. Captura retroactiva de los 3 viajes de mayo
5. Skills de reporte

## Notas de arquitectura
- Mismas reglas que factory3: todo en `skill.py` + `service.py`, nunca lógica inline
- Doble ID en toda tabla: `id` (uuid) + `folio` visible (VIA-001, GAS-001)
- Skills `kind=data` para reportes, expuestos via `GET /data/{skill}`
- Schema Supabase: `logplat` (aislado de `public`)
