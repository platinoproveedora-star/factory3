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
- [ ] Ejecutar SQL en Supabase
- [ ] Correr `vertical_erp/erp_health_check`
- [ ] Crear skills/data APIs de ventas
- [ ] Crear dashboard ventas
- [ ] Actualizar `modules.json` a `active` cuando Supabase este listo

## Pendientes de negocio

- Confirmar si productos tendran costo para margen.
- Confirmar impuestos por default.
- Confirmar condiciones de credito y dias de vencimiento.
- Confirmar si la factura sera solo registro interno o integracion SAT futura.

