# Arquitectura de Agentes — EMP_CONTA4ALL

- **company_id:** `EMP_CONTA4ALL`
- **client_id:** `UC-102`
- **Tipo:** service_company — automatización contable multi-RFC

## Flujo principal

```
Usuario (dashboard) → sube e.firma (.cer + .key) → convierte a base64
        │
        ▼
  sat_cfdi_sync   ← rfc, efirma_creds, fecha_inicio, fecha_fin, tipo (E/R)
        │
        ▼
  cfdi_documentos (schema: uc102_proy001)
        │
        ▼
  sat_cfdi_list   → tablas Ingresos / Egresos en dashboard
```

## Reglas de arquitectura

- Todo código reutilizable recibe identidad por `context`/`project.json`, no hardcode.
- Skills genéricos de `vertical_sat` se usan directamente — no reimplementar.
- Schema Supabase: `uc102_proy001` — se pasa siempre por context.
- Credenciales e.firma: NUNCA se persisten en Supabase. Sólo en env vars de Render o en sesión de usuario (memoria de proceso, no disco).
- `empresa_id` en `cfdi_documentos` usa el RFC del propietario como identificador único por empresa.

## Skills utilizados (todos de `vertical_sat`)

| Skill | Rol |
|---|---|
| `sat_auth` | Obtiene token SAT vía e.firma |
| `sat_cfdi_solicitud` | Solicita paquete de descarga |
| `sat_cfdi_verificar` | Poll de estado hasta paquetes listos |
| `sat_cfdi_descargar` | Descarga ZIP → XMLs |
| `sat_cfdi_parser` | Parsea XML CFDI 3.3/4.0 → dict |
| `sat_cfdi_store` | Upsert en `cfdi_documentos` |
| `sat_cfdi_sync` | Orquestador: hace todo lo anterior |
| `sat_cfdi_list` | `kind=data` — lista/filtra para dashboard |

## Verificación antes de producción

- `factory_no_hardcode_audit` — sin RFCs, schemas ni IDs quemados
- `qa_secrets_check` — env vars declaradas, nunca imprimir valores
- `factory_project_context_resolve` — contexto multiempresa resuelto sin defaults de otro cliente
