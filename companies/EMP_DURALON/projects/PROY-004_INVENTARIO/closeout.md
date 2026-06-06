# Closeout - PROY-004 - Inventario

Closed at: en progreso operativo

## Checklist de cierre

- [x] Schema creado y expuesto en Supabase.
- [x] Health check ERP-ready aprobado.
- [x] Skills registrados y probados.
- [x] Productos clave y reglas de recurrencia base cargadas.
- [x] Dashboard creado.
- [x] Entradas por compra probadas con datos reales.
- [x] Salidas por remision/ajuste probadas con datos reales.
- [x] Costeo por lote, ultimo costo y promedio ponderado conectado.
- [x] Reasignacion auditada de lote en kardex para correcciones operativas.
- [ ] Permisos/autorizacion real pendientes.
- [ ] Pagos/CXC/CXP completos pendientes para modulo posterior.

## Supabase

- Schema: `uc101_proy004`
- Tablas: `erp_products`, `erp_parties`, `erp_kardex`, `erp_recurrence_rules`
- Productos base: `varilla_3_8`, `varilla_1_2`, `cemento`
- Reglas base: alertar diario si no hay compra en 7 dias

## Dashboard

- Ubicacion: `companies/EMP_DURALON/projects/PROY-004_INVENTARIO/dashboard/inventario/`
- Local: `http://localhost:3014`
- Pestañas: inventario, proveedores, clientes, ventas/salidas, compras/entradas
- Estado: build aprobado y lectura real de Supabase validada

## Estado operativo al 2026-06-06

- Dashboard publico: `https://uc101-inventario.onrender.com`.
- Compras: captura multi-renglon con proveedor, producto, lote, cantidad, costo, IVA y entrada automatica al kardex.
- Ventas/salidas: lectura de remisiones desde PROY-002 y salidas en kardex por renglon.
- Producto: alta/edicion de catalogo con marca, categoria, categoria 2, producto clave y minimo.
- Kardex: consulta por producto/rango, ultimos movimientos, lote visible y rango maximo de 2 meses.
- Inventario: tabla por lote primero, costo de compra del lote, inventario actual, productos clave y todos los productos.

## Skills clave

- `vertical_erp_inventory/erp_inventory_product_save`
- `vertical_erp_inventory/erp_inventory_product_update`
- `vertical_erp_inventory/erp_inventory_party_save`
- `vertical_erp_inventory/erp_inventory_party_delete`
- `vertical_erp_inventory/erp_inventory_kardex_save`
- `vertical_erp_inventory/erp_inventory_kardex_list`
- `vertical_erp_inventory/erp_inventory_kardex_lot_reassign`
- `vertical_erp_inventory/erp_inventory_lot_options`
- `vertical_erp_inventory/erp_inventory_lot_stock_report`
- `vertical_erp_inventory/erp_inventory_current_stock_report`
- `vertical_erp_compras/erp_compras_purchase_create`
- `vertical_erp_compras/erp_compras_purchase_list`
- `vertical_erp_costing/*`
