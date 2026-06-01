# Deliverables — PROY-001 — Gastos

`EMP_DURALON` · `UC-101` (legacy) · `module_code: gastos` · Repo: `platinoproveedora-star/uc101-proy001`

## Checklist

- [x] Bot @Duralon1_bot corriendo en factory3
- [x] Captura manual — forma rápida (cantidad,fecha,concepto) + /nuevo paso a paso
- [ ] OCR/AI para fotos de tickets — código listo, depende de créditos Anthropic
- [x] Base de datos — schema `uc101_proy001`, 5 tablas, 12 categorías seed
- [x] Dashboard Next.js deployado en Render — https://uc101-gastos.onrender.com
- [x] KPIs, tabla por categoría, comparativo mensual, tabla de movimientos con búsqueda y export CSV
- [x] README y docs en repo del cliente
- [x] Tania pre-registrada (USR-002) — se vincula automático en su /start
- [ ] Chat ID de Luis — pendiente que haga /start
- [ ] SQL ERP migration en Supabase — ver `sql_erp_migration.sql`
- [x] ERP-ready: identidad empresa_id/project_code/module_code en skills
- [ ] Storage de tickets (bucket nombrado, confirmar si activo)
- [ ] PDF export (no requerido en MVP)

## Estado pendientes críticos

| Pendiente | Bloqueante | Acción |
|---|---|---|
| Chat ID Luis | No (bot funciona para Tania y ACH) | Luis hace /start en @Duralon1_bot |
| SQL ERP Supabase | No (skills usan defaults correctos) | Correr `sql_erp_migration.sql` en SQL Editor |
| OCR tickets | No (captura manual funciona) | Recargar créditos Anthropic |
| Storage tickets | No (gastos se guardan sin foto) | Confirmar bucket en Supabase Storage |

## URLs entregadas

| Recurso | URL |
|---|---|
| Dashboard | https://uc101-gastos.onrender.com |
| Bot | @Duralon1_bot |
| GitHub | https://github.com/platinoproveedora-star/uc101-proy001 |
| Supabase schema | uc101_proy001 (proyecto ddcwdtqiupwtyltdpakm) |
