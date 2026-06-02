# Vertical ERP

## Objetivo

Definir el contrato generico para construir ERPs modulares en Factory3. La vertical no pertenece a una empresa especifica: debe servir para `EMP_DURALON`, empresas internas y clientes freelance que despues puedan crecer de un modulo aislado a un ERP completo.

`vertical_erp` no reemplaza verticales de negocio como `vertical_client_expenses` o `vertical_sales`. Les da una base comun de identidad, tablas, usuarios, folios, eventos e interoperabilidad.

## Principios

- Todo ERP pertenece a una empresa: `empresa_id` / `company_id`.
- Todo proyecto usa `project_code`: `PROY-001`, `PROY-002`, etc.
- Todo modulo usa `module_code`: `gastos`, `ventas`, `inventario`, `compras`, `erp_core`.
- Toda tabla operativa usa doble ID: `id uuid` + `folio text UNIQUE NOT NULL`.
- Todo registro operativo debe tener `empresa_id`, `project_code` y `module_code`.
- Los modulos se conectan por IDs comunes, eventos y data skills; no por dashboards leyendo Supabase directo.
- La logica generica vive en `factory/skills/internos/vertical_erp/`.
- La configuracion especifica vive en `companies/<EMPRESA>/`.

## Contrato Minimo de Tabla

Toda tabla operativa nueva debe incluir:

```sql
id uuid primary key default gen_random_uuid(),
folio text unique not null,
empresa_id text not null,
project_code text not null,
module_code text not null,
created_at timestamptz not null default now(),
updated_at timestamptz
```

## Folios

Los folios internos deben ser estables y no editables. Para documentos comerciales con alto volumen se recomienda usar 5 digitos:

```text
COT-00001
PED-00001
REM-00001
FAC-00001
```

Si el cliente maneja su propia numeracion, conservarla en un campo separado como `external_folio`. El folio interno sigue siendo la referencia Factory/ERP.

Campos opcionales recomendados cuando el modulo pueda conectarse con otros:

```sql
global_user_id uuid null,
customer_id uuid null,
supplier_id uuid null,
sales_order_id uuid null,
purchase_order_id uuid null,
cost_center_id uuid null,
asset_id uuid null,
erp_tags jsonb not null default '{}',
metadata jsonb not null default '{}'
```

## Estructura de Proyecto ERP

Un modulo puede vivir solo:

```text
companies/<EMPRESA>/projects/PROY-001_GASTOS/
  project.json
  deliverables.md
  notes.md
  closeout.md
  assets/
```

Un ERP completo debe tener un proyecto contenedor:

```text
companies/<EMPRESA>/projects/PROY-003_ERP_CORE/
  ERP_ARCHITECTURE.md
  modules.json
  data_contracts.md
  integration_plan.md
  project.json
  deliverables.md
  notes.md
  assets/
```

Regla: si se necesita mover el ERP completo, el proyecto `ERP_CORE` debe contener la arquitectura especifica, contratos y mapa de modulos.

## Modulos Comunes

| Modulo | `module_code` | Vertical de negocio esperada |
|---|---|---|
| Gastos | `gastos` | `vertical_client_expenses` |
| Ventas | `ventas` | `vertical_sales` |
| Inventario | `inventario` | futura `vertical_inventory` |
| Compras | `compras` | futura `vertical_purchasing` |
| Clientes/CRM | `crm` | `vertical_sales` / futura CRM |
| Cuentas por cobrar | `cxc` | `vertical_sales` / `vertical_erp` |
| Cuentas por pagar | `cxp` | futura `vertical_purchasing` |
| ERP central | `erp_core` | `vertical_erp` |

## Skills Iniciales

| Skill | Funcion |
|---|---|
| `vertical_erp/erp_identity_contract` | Devuelve y valida `empresa_id`, `project_code`, `module_code`, schema y columnas requeridas. |
| `vertical_erp/erp_health_check` | Audita si un modulo cumple el contrato ERP-ready. |
| `vertical_erp/erp_module_registry` | Registra o lista modulos activos de una empresa. |
| `vertical_erp/erp_schema_planner` | Genera propuesta SQL para tablas ERP-ready sin ejecutar por default. |
| `vertical_erp/erp_folio_reserve` | Reserva folios internos por schema, scope y prefijo usando secuencia atomica. |
| `vertical_erp/erp_user_mapper` | Mapea usuarios locales a identidad global por Telegram, WhatsApp, phone o email. |
| `vertical_erp/erp_event_logger` | Registra eventos comunes entre modulos. |
| `vertical_erp/erp_cross_module_linker` | Crea relaciones entre registros de distintos modulos. |
| `vertical_erp/erp_dashboard_data` | Expone datos consolidados para dashboard ERP central. |

## Flujo Recomendado

Para un modulo aislado:

```text
erp_identity_contract
-> vertical de negocio especifica
-> erp_health_check
```

Para un ERP completo:

```text
erp_identity_contract
-> erp_module_registry
-> modulos de negocio
-> erp_event_logger / erp_cross_module_linker
-> erp_dashboard_data
-> erp_health_check
```

## Compatibilidad con Clientes Upwork

Un cliente freelance puede iniciar como `UC-###`, pero si se vuelve ERP o empresa operativa debe tener `EMP_<NOMBRE>` como identidad principal.

`UC-###` puede mantenerse como `legacy_client_id`, pero los nuevos registros deben usar:

```text
empresa_id = EMP_<NOMBRE>
project_code = PROY-###
module_code = <modulo>
```

## Reglas de Dashboard

- Dashboards nuevos consumen Factory API por `/data/<skill>`.
- No guardar credenciales Supabase en Vercel o frontends.
- Un dashboard de modulo puede existir solo.
- El dashboard ERP central debe leer datos consolidados por `erp_dashboard_data` o data skills equivalentes.

## Checklist ERP-Ready

Un modulo esta ERP-ready si cumple:

- Tiene `project.json` con `company_id`, `project_code`, `module_code` y schema.
- Sus tablas operativas tienen `id`, `folio`, `empresa_id`, `project_code`, `module_code`.
- Los usuarios pueden mapearse a `global_user_id` o campos equivalentes.
- Usa data skills para dashboard.
- Documenta schema, tablas y pendientes en `docs/TABLES.md` o en contratos del proyecto ERP core.
- Mantiene aliases legacy documentados, sin usarlos como identidad principal.
