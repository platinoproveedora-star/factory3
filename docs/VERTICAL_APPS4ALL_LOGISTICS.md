# Vertical Apps4All Logistics

## Objetivo

`vertical_apps4all_logistics` implementa Logistics4All: modulo multiempresa y multiusuario para armar viajes desde pedidos ERP existentes, programarlos por fecha/hora/duracion, asignar vehiculo y chofer, y mostrarlos en agenda/calendario operativo.

## Principios

- Logistics4All no duplica pedidos: lee contratos de ventas/pedidos y guarda solo viajes, asignaciones y datos logisticos.
- Todo acceso debe resolver `company_id`/`empresa_id`, `project_code`, `module_code`, `schema` y `sales_schema`.
- El dashboard no lee Supabase directo; llama Factory API y los skills de esta vertical.
- Los usuarios solo ven empresas donde tienen grant del modulo `logistics`; `platform_admin` puede cambiar entre empresas.
- Toda tabla operativa usa doble ID: `id uuid` + `folio text UNIQUE NOT NULL`.
- `dry_run=True` por defecto en escrituras y schema setup.

## Contrato de pedidos

La fuente inicial para Duralon es `PROY-002_VENTAS`:

- `sales_documents` con `document_type = pedido`
- `sales_document_items` para partidas
- disponibles: `status in ('pedido', 'liberado')`

Campos esperados:

```text
pedido.id
pedido.folio
pedido.external_folio
pedido.customer_name_snapshot
pedido.due_date
pedido.city
pedido.city_quadrant
pedido.total_weight_kg
pedido.total
items.description/product_name_snapshot
items.quantity
items.unit
items.line_total
items.weight_kg_total
```

## Skills

- `vertical_apps4all_logistics/logistics_schema_setup`
- `vertical_apps4all_logistics/logistics_dashboard_data`
- `vertical_apps4all_logistics/logistics_trip_create`
- `vertical_apps4all_logistics/logistics_trip_assign_orders`
- `vertical_apps4all_logistics/logistics_trip_manage`
- `vertical_apps4all_logistics/logistics_trip_summary`
- `vertical_apps4all_logistics/logistics_calendar_data`
- `vertical_apps4all_logistics/logistics_catalog_manage`

## Estados de viaje

```text
borrador -> programado -> confirmado -> en_ruta -> completado
cancelado
```

Un viaje pasa a `programado` cuando tiene `fecha_viaje`, `hora_inicio`, `duracion_minutos`, `vehiculo_id` y `driver_id`.

## UI

Tabs V1:

- Pedidos: lista pendiente, seleccion manual y asignacion a viaje.
- Viajes: tabla tipo Excel por viaje con pedido, cliente, fecha entrega, peso, partida 1/2/3, otras partidas e importe.
- Calendario: agenda por dia usando fecha/hora/duracion.
- Config: vehiculos, choferes y productos clave.
