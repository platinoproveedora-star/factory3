# Notes - PROY-006 Banks

- Schema previsto: `uc101_proy006`.
- Modulo vendible: cuentas, movimientos, autorizaciones, conciliacion y motor de dinero.
- Contrato tecnico definitivo: `VERTICAL_ERP_BANKS_DEFINITIVO.md`.
- Banks debe ser independiente: billing, compras y reconciliation llaman a Banks; Banks no debe depender de dashboards ni credenciales directas.
- Toda escritura reusable debe recibir `company_id`/`empresa_id`, `project_code`, `module_code` y `schema` por context.
- La logica critica de saldo/autorizacion debe ejecutarse en Postgres via RPC con transaccion y `select ... for update`.
