# Vertical Freelance Growth

## Objetivo
Crear activos para vender servicios de Factory3 en plataformas como Upwork y Pioneer: perfil, portafolio, case studies y propuestas personalizadas.

## Empresa Base
- `companies/EMP_FREELANCE_GROWTH/portfolio/profile.json`
- `companies/EMP_FREELANCE_GROWTH/portfolio/projects.json`
- `companies/EMP_FREELANCE_GROWTH/portfolio/upwork/`
- `companies/EMP_FREELANCE_GROWTH/portfolio/pioneer/`

## Skills MVP
| Skill | Funcion |
|---|---|
| `vertical_freelance_growth/upwork_profile_builder` | Genera `upwork/profile_draft.md` desde perfil y proyectos. |
| `vertical_freelance_growth/upwork_case_study_generator` | Convierte proyectos reales en case studies. |
| `vertical_freelance_growth/upwork_proposal_generator` | Genera propuesta para un job description. |
| `vertical_freelance_growth/upwork_job_matcher` | Evalua una vacante y decide si conviene aplicar. |
| `vertical_freelance_growth/upwork_portfolio_pack_builder` | Prepara proyectos como piezas de portafolio Upwork listas para copiar. |
| `vertical_freelance_growth/factory_portfolio_auditor` | Escanea Factory3 y detecta empresas/dashboards documentables. |
| `vertical_freelance_growth/portfolio_gap_analyzer` | Recomienda screenshots, videos, case studies y pendientes por proyecto. |
| `vertical_freelance_growth/portfolio_project_updater` | Agrega candidatos detectados a `projects.json` cuando se aprueban. |

## Flujo Recomendado
1. Mantener `profile.json` y `projects.json` como fuente de verdad.
2. Generar perfil Upwork.
3. Generar case studies de proyectos reales: LOGPLAT, ESTOIKOLAB, RSTATE y RH1.
4. Usar el generador de propuestas con cada job real.
5. Antes de aplicar, pegar la vacante en `upwork_job_matcher` para score y riesgos.
6. Auditar Factory3 para detectar nuevos proyectos documentables.
7. Fase 2: agregar Pioneer, clientes Upwork y modulo de cursos/manuales.

## Auditoria Automatica
El flujo recomendado para documentacion comercial continua:

1. `factory_portfolio_auditor` detecta empresas, dashboards, verticales y candidatos nuevos.
2. `portfolio_gap_analyzer` genera pendientes de assets: screenshots, videos, links y case studies.
3. `portfolio_project_updater` agrega candidatos aprobados a `projects.json`.
4. Regenerar profile, case studies y portfolio pack.

Meta futura: correr este flujo diariamente a las 23:00 para mantener el portafolio actualizado.
