# Deliverables - PROY-002 - Ventas

Company: `EMP_DURALON`  
Legacy client: `UC-101`  
Module: `ventas`

## Scope

Modulo ERP-ready de ventas para clientes, productos, documentos comerciales, pagos y cuentas por cobrar.

## Checklist

- [x] `project.json`
- [x] `PROJECT_BRIEF.md`
- [x] SQL schema draft ERP-ready
- [x] Modelo documental cotizacion -> pedido -> remision -> factura
- [x] Folios internos de 5 digitos
- [x] `external_folio` solo para pedido/remision/factura
- [x] Ejecutar SQL/migraciones base en Supabase
- [x] Crear skills/data APIs de ventas
- [x] Crear form de caja/remisiones
- [x] Desplegar form en Render
- [x] Integrar remisiones con kardex de PROY-004
- [x] Guardar direccion de entrega por remision
- [x] Generar PDF imprimible
- [x] Integrar snapshot de costeo por lote/promedio/ultimo costo
- [ ] Correr `vertical_erp/erp_health_check`
- [ ] Dashboard ventas completo separado
- [ ] Actualizar `modules.json` a `active` final cuando cierre health check

## Pendientes de negocio

- Costeo base ya definido: costo lote, ultimo costo y promedio ponderado.
- Confirmar impuestos por default.
- Confirmar condiciones de credito, pagos y dias de vencimiento.
- Confirmar si la factura sera solo registro interno o integracion SAT futura.
