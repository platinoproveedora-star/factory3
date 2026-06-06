# ERP Architecture - PROY-003_ERP_CORE

## Objetivo

`PROY-003_ERP_CORE` es el proyecto contenedor del ERP modular de Duralon. Su funcion es guardar la arquitectura movible del ERP: mapa de modulos, contratos de datos, reglas de integracion, dashboard central y handoff.

Los modulos viven como proyectos separados:

| Proyecto | Modulo | Estado | Schema |
|---|---|---|---|
| `PROY-001` | `gastos` | ERP-ready | `uc101_proy001` |
| `PROY-002` | `ventas` | operativo parcial | `uc101_proy002` |
| `PROY-003` | `erp_core` | arquitectura viva | N/A |
| `PROY-004` | `inventario` | operativo | `uc101_proy004` |

## Identidad

```text
empresa_id = EMP_DURALON
company_id = EMP_DURALON
legacy_client_id = UC-101
erp_core_project = PROY-003
```

`UC-101` existe solo como alias legacy. Los nuevos modulos deben usar `EMP_DURALON` como identidad principal.

## Contrato de Tabla

Toda tabla operativa de cualquier modulo debe tener:

```sql
id uuid primary key default gen_random_uuid(),
folio text unique not null,
empresa_id text not null,
project_code text not null,
module_code text not null,
created_at timestamptz not null default now(),
updated_at timestamptz
```

## Comunicacion Entre Modulos

Los modulos no deben depender de dashboards ni credenciales directas. Se comunican por:

- IDs comunes: `customer_id`, `supplier_id`, `sales_order_id`, `purchase_order_id`, `cost_center_id`, `asset_id`.
- Eventos: venta creada, gasto creado, pago recibido, cotizacion aceptada.
- Data skills: endpoints `/data/<skill>` desde Factory API.
- Registros compartidos documentados en `data_contracts.md`.

## Ventas - Documentos Comerciales

Ventas usa una tabla unificada `sales_documents` para:

```text
cotizacion -> pedido -> remision -> factura
```

Folios internos:

```text
COT-00001
PED-00001
REM-00001
FAC-00001
```

`external_folio` solo aplica para `pedido`, `remision` y `factura`. Cotizacion se queda con folio interno.

## Rol de ERP Core

ERP Core debe:

- Registrar modulos activos en `modules.json`.
- Auditar cada modulo con `vertical_erp/erp_health_check`.
- Definir contratos de lectura y escritura.
- Consolidar KPIs para dashboard central.
- Mantener plan de integracion y migracion.
- Ser el paquete movible si el ERP se separa de Factory3 o se entrega como producto.

## Estado Actual al 2026-06-06

- `PROY-001_GASTOS`: estable, ERP-ready, dashboard y bot operativos.
- `PROY-002_VENTAS`: form de caja/remisiones operativo; remision guarda encabezado/items y descuenta kardex.
- `PROY-003_ERP_CORE`: conserva contratos, mapa de modulos y plan movible del ERP.
- `PROY-004_INVENTARIO`: dashboard operativo con productos, clientes/proveedores, compras, ventas/salidas, kardex, lotes y costeo.
- Vertical generica nueva: `vertical_erp_costing` para costo lote, ultimo costo y promedio ponderado.

## Roadmap

1. Confirmar `PROY-001_GASTOS` como ERP-ready.
2. Crear `PROY-002_VENTAS` con contrato `vertical_erp`.
3. Ejecutar y auditar schema ventas en Supabase.
4. Crear data contracts entre gastos y ventas.
5. Diseñar dashboard ERP central.
6. Agregar inventario/compras si el negocio lo requiere.

## Roadmap actualizado

1. Capturar ventas reales de mayo/junio y validar saldos por lote.
2. Normalizar captura de lotes para evitar duplicados por escritura.
3. Crear modulo de pagos/CXC/CXP cuando la operacion de inventario este estable.
4. Implementar permisos/autorizacion real.
5. Diseñar dashboard ERP central consolidado.
