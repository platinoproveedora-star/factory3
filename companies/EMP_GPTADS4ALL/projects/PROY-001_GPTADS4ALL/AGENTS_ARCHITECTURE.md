# Arquitectura del proyecto

- company_id: `EMP_GPTADS4ALL`
- project_code: `PROY-001`
- module_code: `gptads4all`
- schema: `gptads4all`

Reglas:
- Todo codigo reusable recibe identidad por context/config.
- No hardcodear empresa, schema, project_code, URLs ni tokens.
- Skills vendibles viven en `factory/skills/internos/vertical_gptads4all/`.
- Antes de cierre correr `factory_no_hardcode_audit`.
