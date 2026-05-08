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

```
ANTHROPIC_API_KEY   # scoring IA y generacion de seeds
SUPABASE_URL        # conexion a Supabase
SUPABASE_KEY        # service role key (nunca anon)
TELEGRAM_TOKEN_ADMIN_BOT   # token del bot admin
RH_EMPRESA_ID       # ID de empresa por defecto (ej: rh_empresa_1)
DASHBOARD_URL       # URL del dashboard Streamlit en Render
```

## Esquema de tablas (doble ID)

Toda tabla tiene:
- `id` UUID — interno, nunca se muestra al usuario, se usa en JOINs
- `folio` TEXT — visible al usuario, usado en comandos (VAC-001, CAND-001)

```sql
vacantes       (id, folio, empresa_id, titulo, descripcion, requisitos, canal, estado, tipo)
candidatos     (id, folio, vacante_id, nombre, telefono, email, canal, canal_user_id, estado)
conversaciones (id, candidato_id, vacante_id, canal, estado, cuestionario_paso)
respuestas     (id, candidato_id, vacante_id, pregunta, respuesta, orden)
scores         (id, candidato_id, vacante_id, score_total, pasa_knockout, detalle)
pipeline       (id, candidato_id, vacante_id, etapa, notas)
eventos_historial (id, candidato_id, tipo_evento, datos)
cuestionarios  (id, empresa_id, vacante_id, puesto, profundidad, canal, preguntas)
test_seeds     (id, seed_label, empresa_id, tabla, registro_id)
bot_states     (id, chat_id, state, updated_at)
```

## Bot admin — modo RH (/rh1)

Comandos disponibles en modo RH:

```
/vacantes              — listar vacantes con folio
/ranking N             — top candidatos de vacante (por folio o numero)
/reporte N             — resumen pipeline de vacante
/candidatos N          — candidatos de una vacante
/candidato FOLIO       — detalle de un candidato (CAND-001)
/mover FOLIO etapa     — mover candidato en pipeline
/seed N                — crear N vacantes con candidatos (background)
/seedc N FOLIO         — agregar N candidatos a vacante existente (background)
/seeds                 — listar seeds generados
/limpiar LABEL         — borrar seed completo
/status                — resumen general del sistema
/dashboard             — link al dashboard Streamlit
/ayuda                 — lista de comandos
```

## Dashboard (Streamlit)

5 páginas:
- **Overview** — KPIs: vacantes activas, candidatos, score promedio, seeds
- **Vacantes** — tabla filtrable por estado/tipo/titulo
- **Candidatos** — tabla con scores y KO flag
- **Pipeline** — vista kanban por etapa
- **Seeds** — lista de seeds con conteos por tabla

Servicio separado en Render: `factory3-dashboard`
Archivos: `EMP_RH1/dashboard/app.py`, `EMP_RH1/dashboard/db.py`, `EMP_RH1/dashboard/requirements.txt`

## Tipo de vacante

```
tipo = "real"   # vacante de produccion
tipo = "seed"   # vacante de prueba (creada por /seed)
```
Permite filtrar datos de prueba sin borrarlos.

## Etapas del proyecto

### Etapa 1 — MVP (completo)
- Bot admin con modo /rh1
- Comandos: vacantes, candidatos, ranking, reporte, mover, seed, seedc, seeds, limpiar, status, dashboard
- Sistema de folios (VAC-001, CAND-001)
- Dashboard Streamlit
- Seeds con IA (Anthropic Haiku)
- Background tasks para operaciones largas

### Etapa 2 — Enriquecimiento
- CV parser
- Bot de captura para candidatos reales
- Analitica avanzada en dashboard
- Alertas a manager via Telegram

### Etapa 3 — Optimizacion
- Integraciones ATS externas
- Reportes PDF
- Automatizacion de campanas
