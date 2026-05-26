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

## Flujo Recomendado
1. Mantener `profile.json` y `projects.json` como fuente de verdad.
2. Generar perfil Upwork.
3. Generar case studies de proyectos reales: LOGPLAT, ESTOIKOLAB, RSTATE y RH1.
4. Usar el generador de propuestas con cada job real.
5. Antes de aplicar, pegar la vacante en `upwork_job_matcher` para score y riesgos.
6. Fase 2: agregar Pioneer y modulo de cursos/manuales.
