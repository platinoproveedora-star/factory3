# Arquitectura del proyecto

- company_id: `EMP_DRENAFORT`
- project_code: `PROY-001`
- module_code: `inventario`
- schema: `drenafort_proy001`

Reglas:
- Todo codigo reusable recibe identidad por context/config.
- No hardcodear empresa, schema, project_code, URLs ni tokens.
- Antes de cierre correr `factory_no_hardcode_audit`.
