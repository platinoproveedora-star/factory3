# Companies Standard

Este documento define como debe estructurarse cualquier empresa dentro de `companies/`.

## Objetivo

Cada empresa debe ser una unidad operativa clara: configuracion, dashboard, datos, conocimiento, clientes, campanas y documentacion. Las empresas no deben duplicar skills genericos; deben configurarlos.

## Estructura Base

```text
companies/<EMPRESA>/
  README.md
  company.config.json
  AGENTS_ARCHITECTURE.md
  dashboard/
    app.py
    requirements.txt
    render.yaml
  clients/
    registry.json
  campaigns/
  portfolio/
  knowledge/
  schemas/
  assets/
```

No todas las carpetas son obligatorias desde el dia uno, pero deben usarse estos nombres cuando apliquen.

## Carpetas

| Carpeta | Uso |
|---|---|
| `dashboard/` | UI operativa de la empresa. |
| `clients/` | Clientes de esa empresa, si la empresa vende/atiende clientes. |
| `campaigns/` | Campanas por slug o consecutivo. |
| `portfolio/` | Activos comerciales, case studies, auditorias y proyectos vendibles. |
| `knowledge/` | Base de conocimiento para agentes IA. |
| `schemas/` | SQL, migraciones o contratos de datos. |
| `assets/` | Imagenes, videos y documentos de trabajo no secretos. |

## `company.config.json`

Contrato minimo:

```json
{
  "company_id": "EMP_EXAMPLE",
  "company_name": "Example Company",
  "company_type": "service_company",
  "industry": "ai_automation",
  "status": "active",
  "dashboards": [],
  "skill_stack": [],
  "channels": [],
  "storage": {
    "supabase_schema": "",
    "buckets": []
  }
}
```

## Reglas

- El nombre de empresa debe ser estable y en mayusculas: `EMP_<DOMINIO>`.
- El dashboard principal debe registrarse en `docs/DASHBOARDS.md`.
- Si usa Supabase, sus tablas deben registrarse en `docs/TABLES.md`.
- Si usa nuevos skills, la vertical debe documentarse en `docs/VERTICAL_<NOMBRE>.md`.
- No guardar secretos dentro de `companies/`; usar variables de entorno.
- No usar nombres largos para codigos operativos; usar consecutivos legibles.

## Tipos Comunes de Empresa

| Tipo | Ejemplo | Carpetas principales |
|---|---|---|
| Campanas | `EMP_CAMP_RSTATE` | `campaigns/`, `landing/`, `dashboard/` |
| Agentes IA | `EMP_ESTOIKOLAB` | `agents/`, `knowledge/`, `dashboard/` |
| Freelance/ventas | `EMP_FREELANCE_GROWTH` | `clients/`, `portfolio/`, `dashboard/` |
| Operacion cliente | `EMP_LOGPLAT` | `dashboard/`, schemas Supabase, docs operativas |

## Checklist de Empresa Nueva

- Crear carpeta `companies/<EMPRESA>/`.
- Crear `README.md`.
- Crear `company.config.json`.
- Registrar dashboard si existe.
- Registrar tablas si existen.
- Documentar verticales nuevas.
- Definir si tendra `clients/`, `campaigns/`, `knowledge/` o `portfolio/`.
