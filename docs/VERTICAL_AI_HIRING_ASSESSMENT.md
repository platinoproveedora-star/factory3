# Vertical: ai_hiring_assessment

Evaluación automatizada de candidatos usando IA. Complementa el funnel de `mass_digital_hiring` y `vertical_rh` con análisis profundo por dimensión, cuestionarios adaptados al contratista y agendado de entrevistas con notificación automática.

## Skills

| Skill | Descripción |
|---|---|
| `rh_dimension_analyzer` | Analiza una dimensión específica del candidato (conducta, fisico, compromiso, maquinaria, rutas, tecnico). Score 1-10 + señales + recomendación |
| `rh_contractor_interview` | Genera cuestionario de entrevista adaptado al contratista, equipo que opera, zona y canal de comunicación |
| `rh_interview_scheduler` | Agenda entrevistas, auto-asigna slot hábil, notifica candidato y reclutador por Telegram |

## Tablas Supabase usadas

| Tabla | Uso |
|---|---|
| `entrevistas` | Entrevistas agendadas (rh_interview_scheduler escribe) |
| `reclutadores` | Datos del reclutador para notificación (lectura) |
| `candidatos` | Nombre y canal_user_id del candidato (lectura) |
| `respuestas` | Respuestas del candidato para análisis (rh_dimension_analyzer lee) |
| `scores` | Resultado del análisis por dimensión (rh_dimension_analyzer escribe) |
| `cuestionarios` | Cuestionario generado por contratista (rh_contractor_interview escribe) |

## Flujo típico

```
1. rh_contractor_interview  →  genera preguntas para el contratista
2. rh_conversation_manager  →  conduce la entrevista por Telegram
3. rh_dimension_analyzer    →  evalúa múltiples dimensiones con las respuestas
4. rh_interview_scheduler   →  agenda entrevista presencial si score >= umbral
```

## Variables de entorno

| Variable | Uso |
|---|---|
| `ANTHROPIC_API_KEY` | rh_dimension_analyzer + rh_contractor_interview |
| `SUPABASE_URL` | todas las tablas |
| `SUPABASE_KEY` | todas las tablas |

## Bundle

`factory/skills/active/ai_hiring_assessment.json`
