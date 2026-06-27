# EMP_CONTA4ALL — Conta4all Automatización Contable

**Client ID:** UC-102  
**Tipo:** service_company  
**Industria:** accounting_automation

## Qué hace

Conta4all es un servicio de automatización contable multi-cliente (varios RFCs) que descarga, organiza y consulta CFDIs del SAT vía e.firma de forma automática.

## Proyectos

| Proyecto | Código | Schema Supabase | Estado |
|---|---|---|---|
| SAT CFDI Sync | PROY-001_SAT | `uc102_proy001` | activo |

## Verticales usadas

- `vertical_sat` — descarga masiva SAT (8 skills)

## Deploy

- Dashboard: `uc102-conta4all-sat` en Vercel
- Backend: Factory API central (`factory3`)

## Estructura

```
EMP_CONTA4ALL/
  company.config.json
  README.md
  AGENTS_ARCHITECTURE.md
  projects/
    PROY-001_SAT/
      project.json
      AGENTS_ARCHITECTURE.md
      schema.sql
      .env.example
      dashboard/
        app.py
        requirements.txt
        render.yaml
```

## Env vars por cliente (se configuran en Render por RFC)

| Variable | Descripción |
|---|---|
| `SAT_RFC` | RFC del contribuyente |
| `SAT_EFIRMA_CER_B64` | Certificado .cer en base64 |
| `SAT_EFIRMA_KEY_B64` | Llave privada .key en base64 |
| `SAT_EFIRMA_PASSWORD` | Contraseña de la llave privada |
| `SUPABASE_URL` | URL de Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Clave de servicio Supabase |
