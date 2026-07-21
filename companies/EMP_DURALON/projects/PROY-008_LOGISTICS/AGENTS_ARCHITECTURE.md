# Arquitectura del proyecto

- company_id: `EMP_DURALON`
- project_code: `PROY-008`
- module_code: `logistics`
- schema: `uc101_proy008`

Reglas:
- Todo codigo reusable recibe identidad por context/config.
- No hardcodear empresa, schema, project_code, URLs ni tokens.
- Antes de cierre correr `factory_no_hardcode_audit`.
