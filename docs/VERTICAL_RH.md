# vertical_rh

Sistema de captura, filtrado y priorizacion de candidatos.
No es un sistema de reclutamiento completo — es una maquina de:
captura → filtrado → priorizacion de talento.

## Flujo maestro

```
vacante → publicacion → entrada canal → bot_inbox_router
→ bot_form_capture → rh_candidate_profile_builder
→ rh_basic_validation → rh_duplicate_detector
→ rh_knockout_filter → rh_candidate_scoring
→ rh_pipeline_manager → rh_candidate_ranking
→ telegram_send_message (followup) → telegram_send_message (alerta manager)
→ supabase_insert_row (persistencia) → rh_report_generator
```

## Skills — 14 nuevos (vertical_rh)

| # | Skill | Descripcion | Estado |
|---|---|---|---|
| 1 | `rh_job_post_generator` | Genera texto de vacante listo para publicar | Pendiente |
| 2 | `rh_questionnaire_generator` | Genera cuestionario segun profundidad (simple/medio/robusto/custom), canal y vertical | Pendiente |
| 3 | `rh_candidate_profile_builder` | Construye perfil estructurado del candidato desde respuestas | Pendiente |
| 4 | `rh_basic_validation` | Valida datos minimos del candidato (nombre, contacto, disponibilidad) | Pendiente |
| 5 | `rh_duplicate_detector` | Detecta candidatos duplicados por telefono, email o user_id | Pendiente |
| 6 | `rh_knockout_filter` | Aplica filtros obligatorios — pasa/no pasa sin puntos medios | Pendiente |
| 7 | `rh_candidate_scoring` | Puntaje basado en requisitos, experiencia, ubicacion, disponibilidad | Pendiente |
| 8 | `rh_pipeline_manager` | Manejo de etapas y estatus del candidato | Pendiente |
| 9 | `rh_candidate_ranking` | Ordena candidatos por prioridad dentro de una vacante | Pendiente |
| 10 | `rh_report_generator` | Reportes basicos de pipeline, scores y conversion | Pendiente |
| 11 | `rh_candidate_search` | Busqueda de candidatos por filtros | Pendiente |
| 12 | `rh_candidate_history` | Historial completo de un candidato | Pendiente |
| 13 | `rh_vacante_store` | Guarda y recupera vacantes en Supabase | Pendiente |
| 14 | `rh_conversation_manager` | Maneja estado de conversacion activa multi-turno | Pendiente |

## Skills de otras verticales que se reutilizan

| Skill existente | Uso en RH |
|---|---|
| `supabase_insert_row` | Guardar candidatos, respuestas, scores |
| `supabase_query_table` | Buscar candidatos, detectar duplicados |
| `supabase_update_row` | Actualizar estatus y pipeline |
| `telegram_send_message` | Followup al candidato + alerta al manager |
| `ig_reply_dm` | Followup por Instagram |
| `bot_inbox_router` | Router de entrada multicanal |
| `bot_form_capture` | Cuestionario conversacional |
| `ig_post_image` | Publicar vacante en Instagram |
| `ig_post_carousel` | Vacante en formato carrusel |
| `rh_job_post_generator` | Generar el texto antes de publicar |

## Logica de cuestionario

```
simple   → 5 preguntas
medio    → 8-12 preguntas
robusto  → 15-25 preguntas
custom   → generado por prompt
```

## Logica de scoring

```
requisitos_obligatorios → pasa / no pasa (knockout)
experiencia             → puntos
ubicacion               → puntos
disponibilidad          → puntos
documentos              → puntos
respuestas_calidad      → puntos (via Anthropic)
```

## Logica de pipeline

```
incompleto      → followup automatico
duplicado       → merge con historial existente
no pasa knockout → rechazado automatico
score alto      → listo_entrevista
score medio     → revision manual
score bajo      → descartado
```

## Estados de candidato

```
nuevo | capturando_datos | incompleto | duplicado
no_apto | apto | listo_entrevista | entrevistado
contratado | rechazado
```

## Tablas Supabase necesarias (9 nuevas)

```sql
vacantes
candidatos
conversaciones
mensajes
respuestas
scores
pipeline
eventos_historial
alertas
```

Mas las 2 base del engine: `sessions`, `agent_memory`

## Variables de entorno

No requiere variables propias.
Usa: ANTHROPIC_API_KEY (scoring con IA), SUPABASE_*, TELEGRAM_TOKEN.

## Etapas

### Etapa 1 — MVP funcional (actual)
Los 14 skills de arriba + bot RH basico con Telegram.
Resultado: recibe candidatos, filtra, organiza pipeline, notifica, guarda todo.

### Etapa 2 — Comunidad y enriquecimiento (siguiente)
- CV parser
- Enrichment de perfil
- Analitica avanzada
- Automatizacion completa de campanas

### Etapa 3 — Optimizacion
- Optimizacion de campanas
- Integraciones ATS externas
- Reportes avanzados

## Bot RH

Un bot dedicado conectado a esta vertical.
Usa `bot_inbox_router` + `bot_form_capture` para el flujo conversacional.
Modo admin para testing sin afectar produccion.

## Tiempo estimado MVP

Skills: 3-5 dias
Bot + tablas Supabase: 1-2 dias adicionales
Total operativo real: 1-2 semanas
