# Factory Architecture

Este documento define la estructura base de Factory3. Debe usarse como referencia antes de crear empresas, dashboards, skills, clientes o proyectos nuevos.

## Principio Central

Factory3 separa capacidades genericas de configuracion por empresa.

| Capa | Ubicacion | Que contiene |
|---|---|---|
| Motor | `factory/` | Skills, engine, loaders, runners y utilidades reutilizables. |
| Empresas | `companies/` | Configuracion, dashboards, clientes, campanas, conocimiento y datos propios de cada empresa. |
| Dashboards | `companies/<EMPRESA>/dashboard/` o `dashboards/` | Interfaces operativas registradas en `docs/DASHBOARDS.md`. |
| Documentacion | `docs/` | Arquitectura, verticales, tablas, dashboards, flujos y reglas comunes. |
| Servicios externos | Supabase, Render, GitHub, Meta, Telegram, WhatsApp | Persistencia, despliegue, repos, anuncios y canales. |

## Reglas de Ubicacion

- Si sirve para muchas empresas, vive en `factory/skills/internos/<vertical>/`.
- Si solo cambia por cliente, tono, industria, presupuesto o canal, vive en `companies/<EMPRESA>/`.
- Si es una regla comun de fabrica, vive en `docs/`.
- Si es un dashboard operativo de una empresa, vive dentro de esa empresa.
- Si crea tablas, dashboards o skills, debe actualizar su registry correspondiente.

## Estructura Recomendada

```text
factory3/
  factory/
    engine/
    skills/
      internos/
        vertical_<dominio>/
  companies/
    <EMPRESA>/
      company.config.json
      README.md
      dashboard/
      clients/
      campaigns/
      portfolio/
      knowledge/
      schemas/
  docs/
    DASHBOARDS.md
    TABLES.md
    REGISTRIES.md
    COMPANIES_STANDARD.md
    CLIENTS_WORKFLOW.md
```

## Skills

Cada skill debe tener:

```text
factory/skills/internos/<vertical>/<skill>/
  manifest.json
  skill.py
  service.py
```

Todo skill nuevo debe registrarse en `factory/skills/registry.json` y documentarse en `docs/VERTICAL_<NOMBRE>.md`.

## Dashboards

Cada dashboard debe:

- Tener `app.py`, `requirements.txt` y, si aplica, `render.yaml`.
- Cargar skills usando `SkillRunner` y `SkillLoader`.
- Registrar su existencia en `docs/DASHBOARDS.md`.
- Registrar tablas usadas en `docs/TABLES.md`.
- Evitar guardar informacion critica solo en disco local de Render.

## Persistencia

Orden recomendado:

1. GitHub para configuracion, documentacion y entregables de clientes.
2. Supabase para datos operativos vivos.
3. Storage para archivos grandes: imagenes, videos, documentos.
4. Disco local solo para desarrollo o cache temporal.

Para clientes externos, GitHub es la primera fuente de verdad. Supabase complementa con operacion viva como estados, tiempo trabajado, alertas y metricas.

## Decision Rapida

| Caso | Donde va |
|---|---|
| Skill reutilizable | `factory/skills/internos/vertical_<dominio>/` |
| Dashboard de una empresa | `companies/<EMPRESA>/dashboard/` |
| Cliente freelance ganado | `companies/EMP_FREELANCE_GROWTH/clients/` |
| Proyecto para portafolio | `companies/EMP_FREELANCE_GROWTH/portfolio/projects.json` |
| Tabla nueva Supabase | SQL en empresa o `docs/`, registro en `docs/TABLES.md` |
| Regla de estructura comun | `docs/COMPANIES_STANDARD.md` o `docs/CLIENTS_WORKFLOW.md` |
