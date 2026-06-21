# Arquitectura PROY-007 — Bank Statement Converter

- company_id: `EMP_DURALON`
- project_code: `PROY-007`
- module_code: `bank_statement_converter`
- schema: `uc101_proy007`

## Vertical

`vertical_bank_statement_converter` — extracción, normalización, validación y exportación de estados de cuenta bancarios.

## Reglas

- Todo codigo reusable recibe identidad por context/config.
- No hardcodear empresa, schema, project_code, URLs ni tokens.
- Skills viven en `factory/skills/internos/vertical_bank_statement_converter/`.
- Antes de cierre correr `factory_no_hardcode_audit` y `erp_health_check`.
- Ver spec completa: `docs/VERTICAL_BANK_STATEMENT_CONVERTER.md`.
