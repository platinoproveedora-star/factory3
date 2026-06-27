# Arquitectura PROY-001 — SAT CFDI Sync

- **company_id:** `EMP_CONTA4ALL`
- **project_code:** `PROY-001`
- **module_code:** `sat_cfdi_sync`
- **schema:** `uc102_proy001`

## Vertical

`vertical_sat` — autenticación, solicitud, verificación, descarga, parseo y almacenamiento de CFDIs del SAT México via Descarga Masiva.

## Flujo

```
e.firma (.cer + .key + password) + RFC + rango fechas
         │
         ▼
    sat_auth           → token SOAP (5 min)
         │
         ▼
sat_cfdi_solicitud     → id_solicitud
         │
         ▼
sat_cfdi_verificar     → poll → ids de paquetes listos
         │ (por paquete)
         ▼
sat_cfdi_descargar     → ZIP → XMLs
         │
         ▼
sat_cfdi_parser        → dicts estructurados
         │
         ▼
sat_cfdi_store         → upsert uc102_proy001.cfdi_documentos
         │
         ▼
sat_cfdi_list          → dashboard (Ingresos / Egresos)
```

Orquestador: `sat_cfdi_sync` ejecuta todo en una llamada.

## Reglas de diseño

- `schema` y `company_id` siempre por context/project.json — sin hardcode.
- Credenciales e.firma: sólo en env vars de Render o en sesión del usuario (no se persisten en DB).
- Multi-RFC: cada instancia del dashboard tiene sus propias env vars de RFC/e.firma.
- `rfc_propietario` en `cfdi_documentos` identifica al RFC dueño de la descarga.
- Partición automática de rangos > 12 meses en el dashboard.

## Verificación antes de producción

```bash
factory_no_hardcode_audit   # 0 blockers en companies/EMP_CONTA4ALL/
qa_secrets_check            # verificar 6 env vars presentes en Render
skill_safety_eval           # sobre sat_cfdi_solicitud/service.py
```
