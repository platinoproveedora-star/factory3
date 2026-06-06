# Closeout - PROY-002 - Ventas

Closed at: en progreso operativo

## Delivered URLs

| Recurso | URL |
|---|---|
| Form caja/remisiones | https://uc101-remisiones.onrender.com |
| Supabase schema | `uc101_proy002` |
| Factory API | https://factory3.onrender.com |
| Dashboard ventas | Integrado parcialmente en PROY-004 inventario |

## Checklist de cierre

- [x] Schema creado y expuesto en Supabase.
- [x] Skills de ventas creados/registrados.
- [x] Form de caja/remisiones desplegado.
- [x] Remision crea encabezado e items en `uc101_proy002`.
- [x] Remision dispara salida en kardex `uc101_proy004`.
- [x] PDF imprimible de remision.
- [x] Cliente nuevo desde form cuando no existe.
- [x] Snapshot de costos por venta conectado a `vertical_erp_costing`.
- [ ] Health check ERP-ready formal pendiente de correr/documentar.
- [ ] CXC/pagos completos pendientes para modulo futuro de pagos.

## Estado operativo

- Uso actual: caja de ventas/remisiones.
- Documento principal: `sales_documents.document_type = remision`.
- Renglones: `sales_document_items`, con producto, lote, cantidad, precio, IVA y snapshots de costo.
- Conexion inventario: cada renglon de remision crea una salida `source_type=remision` en `erp_kardex`.
- Clientes compartidos: se usa `uc101_proy004.erp_parties`, no tabla separada de clientes para la operacion actual.

## Skills clave

- `vertical_erp_ventas/erp_ventas_customer_list`
- `vertical_erp_ventas/erp_ventas_product_list`
- `vertical_erp_ventas/erp_ventas_customer_get_or_create`
- `vertical_erp_ventas/erp_ventas_remision_create`
- `vertical_erp_ventas/erp_ventas_remision_list`
- `vertical_erp_ventas/erp_ventas_remision_detail`
- `vertical_erp_ventas/erp_ventas_remision_pdf`
- `vertical_erp_ventas/erp_ventas_key_product_matrix`
