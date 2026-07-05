# Arquitectura del proyecto

- company_id: `EMP_FLEET4ALL`
- project_code: `PROY-001`
- module_code: `fleet4all`
- schema: `fleet4all`

Reglas:
- Todo codigo reusable recibe identidad por context/config.
- No hardcodear empresa, schema, project_code, URLs ni tokens.
- Antes de cierre correr `factory_no_hardcode_audit`.

Notas del plan Fleet4All (`docs/fleet4all_plan/`):
- Logica reusable vive en `factory/skills/internos/vertical_fleet4all_{modulo}/`.
- No aplicar `02_SCHEMA_FLEET4ALL.sql` sin aprobacion humana.
- Solo lectura, jamas editar (se clona logica, no se importa): `EMP_LOGPLAT/` y `vertical_emp_logplat/`.
- Tenant de prueba durante desarrollo: `empresa_id=EMP_DEMO_FLEET`.
- Primer tenant real (post smoke F1, migracion pendiente de aprobacion): `EMP_LOGPLAT` (Platino Logistica).
