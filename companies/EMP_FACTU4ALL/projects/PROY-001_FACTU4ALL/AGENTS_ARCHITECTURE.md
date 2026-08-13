# Arquitectura del proyecto

- company_id: `EMP_FACTU4ALL`
- project_code: `PROY-001`
- module_code: `factu4all`
- schema: `factu4all`

Reglas:
- Todo codigo reusable recibe identidad por context/config.
- No hardcodear empresa, schema, project_code, URLs ni tokens.
- Antes de cierre correr `factory_no_hardcode_audit`.
