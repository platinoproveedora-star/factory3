# ERP_ARCHITECTURE — EMP_DURALON

## Identidad

| Campo | Valor |
|---|---|
| `empresa_id` / `company_id` | `EMP_DURALON` |
| `legacy_client_id` | `UC-101` |
| Nombre legal | COMERCIALIZADORA DURALON DE CHIAPAS SA DE CV |

## Módulos

| Código | Nombre | Schema Supabase | Status |
|---|---|---|---|
| PROY-001 | gastos | `uc101_proy001` | activo |
| PROY-002 | ventas | `uc101_proy002` | pendiente |

## Reglas de arquitectura

1. **Doble ID en toda tabla**: `id uuid PRIMARY KEY` (interno) + `folio text UNIQUE NOT NULL` (visible: GAS-001, VEN-001)
2. **Triple identidad en todo registro operativo**: `empresa_id` + `project_code` + `module_code`
3. **Schema separado por módulo**: cada PROY usa su propio schema PostgreSQL en Supabase
4. **Alias legacy**: `UC-101` → `EMP_DURALON` (compatibilidad hacia atrás garantizada en `client_projects.json`)

## Columnas estándar en todas las tablas operativas

```sql
empresa_id   text NOT NULL DEFAULT 'EMP_DURALON',
project_code text NOT NULL DEFAULT 'PROY-001',   -- ajustar por módulo
module_code  text NOT NULL DEFAULT 'gastos'       -- ajustar por módulo
```

## Columnas ERP en tabla `gastos`

Permiten conectar gastos con otros módulos futuros:

```sql
cost_center_id    uuid NULL,   -- centro de costo
customer_id       uuid NULL,   -- cliente (PROY-002 ventas)
supplier_id       uuid NULL,   -- proveedor (PROY-003 compras)
sales_order_id    uuid NULL,   -- orden de venta
purchase_order_id uuid NULL,   -- orden de compra
asset_id          uuid NULL,   -- activo fijo
erp_tags          jsonb NOT NULL DEFAULT '{}'  -- metadatos libres
```

## Columnas ERP en tabla `usuarios`

```sql
global_user_id  uuid NULL,                          -- ID en sistema global futuro
phone           text NULL,
email           text NULL,
modules_allowed text[] NOT NULL DEFAULT ARRAY['gastos']  -- acceso por módulo
```

## Flujo de conexión PROY-001 → PROY-002

Cuando un gasto se vincule a una venta:
```
gastos.sales_order_id → ventas.id (PROY-002)
```

## SQL pendiente en Supabase

Ejecutar en SQL Editor de Supabase (proyecto `ddcwdtqiupwtyltdpakm`):

```sql
-- Ver archivo: companies/EMP_DURALON/projects/PROY-001_GASTOS/sql_erp_migration.sql
```

## Infraestructura

- **Factory API**: https://factory3.onrender.com
- **Dashboard gastos**: https://uc101-gastos.onrender.com
- **Bot**: @Duralon1_bot (token: `UC101_PROY001_BOT_TOKEN`)
- **Supabase**: proyecto `ddcwdtqiupwtyltdpakm`
