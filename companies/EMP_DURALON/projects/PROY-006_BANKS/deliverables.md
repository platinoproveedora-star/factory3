# Deliverables - PROY-006 Banks

- [x] Contexto vendible del proyecto (`project.json`) y registro en `modules.json`.
- [x] Migracion SQL generica de Banks segun `VERTICAL_ERP_BANKS_DEFINITIVO.md`.
- [x] RPC `banks_record_movement()` con idempotencia, autorizaciones y lock de cuenta.
- [x] RPC `banks_decide_authorization()` con lock de movimiento y cuenta.
- [x] Trigger `banks_movements_protect_trg` para inmutabilidad real.
- [x] Skills nuevos: `erp_banks_authorization_decide`, `erp_banks_mark_reconciled`, `erp_banks_consolidated_dashboard`.
- [x] Registro de skills en `factory/skills/registry.json`.
- [x] Schema `uc101_proy006` expuesto y verificado via REST/RPC.
- [x] Dashboard Next.js para Render (`uc101-bancos`) con clave simple y API server-side.
- [ ] Health check ERP y auditoria anti-hardcode con 0 blockers.
- [ ] Pruebas reales: cuenta, movimiento normal, idempotencia, autorizacion, rechazo y conciliacion.
