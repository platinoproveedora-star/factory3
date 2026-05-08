# Tablas Supabase — Registry

Schema: `public` | Actualizado: 2026-05-07

## Índice

| Tabla | Vertical | Descripción |
|---|---|---|
| [agent_memory](#agent_memory) | factory | Memoria persistente de agentes |
| [entrevistas](#entrevistas) | ai_hiring_assessment | Entrevistas agendadas por candidato y reclutador |
| [reclutadores](#reclutadores) | mass_digital_hiring | Reclutadores activos para asignación de candidatos |
| [alertas](#alertas) | vertical_rh | Alertas enviadas a candidatos |
| [bot_states](#bot_states) | factory | Estado de sesión por chat_id de Telegram |
| [candidatos](#candidatos) | vertical_rh | Candidatos registrados — tabla central del funnel |
| [conversaciones](#conversaciones) | vertical_rh | Estado de conversación activa por candidato y vacante |
| [cuestionarios](#cuestionarios) | vertical_rh | Cuestionarios generados por vacante |
| [eventos_historial](#eventos_historial) | vertical_rh | Log de eventos por candidato |
| [fb_grupos](#fb_grupos) | vertical_facebook | Grupos de Facebook descubiertos para publicar |
| [fb_publicaciones](#fb_publicaciones) | vertical_facebook | Registro de posts publicados en grupos FB |
| [mensajes](#mensajes) | factory | Mensajes dentro de una conversación |
| [onboarding_docs](#onboarding_docs) | vertical_tractohub | Documentos recopilados en onboarding de operador |
| [pipeline](#pipeline) | vertical_rh | Historial de etapas por candidato |
| [respuestas](#respuestas) | vertical_rh | Respuestas del candidato al cuestionario |
| [scores](#scores) | vertical_rh | Puntuación y resultado knockout por candidato |
| [test_seeds](#test_seeds) | factory | Registro de IDs generados por seeds de prueba |
| [vacantes](#vacantes) | vertical_rh | Vacantes activas por empresa |
| [whatsapp_broadcasts](#whatsapp_broadcasts) | vertical_whatsapp | Broadcasts enviados o programados por WhatsApp |

---

## agent_memory

Memoria persistente de agentes. Usada por `add_agent_memory_supabase`.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `agent_name` | text | NO | — | Nombre del agente |
| `user_id` | text | NO | — | ID externo del usuario (plataforma) |
| `memory_type` | text | SÍ | 'fact' | Tipo de memoria |
| `content` | text | NO | — | Contenido de la memoria |
| `metadata` | jsonb | SÍ | {} | Metadatos adicionales |
| `created_at` | timestamptz | SÍ | now() | — |
| `updated_at` | timestamptz | SÍ | now() | — |

---

## alertas

Alertas y notificaciones enviadas a candidatos.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `candidato_id` | uuid | NO | — | FK → candidatos.id |
| `tipo` | text | NO | — | Tipo de alerta |
| `canal` | text | NO | — | Canal de envío (telegram, whatsapp…) |
| `mensaje` | text | SÍ | — | Texto enviado |
| `enviado` | boolean | SÍ | false | Si fue enviado exitosamente |
| `created_at` | timestamptz | SÍ | now() | — |

---

## bot_states

Estado de sesión del bot por chat. Persiste el `state` entre mensajes de Telegram.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `chat_id` | text | NO | — | ID del chat de Telegram (externo) |
| `state` | jsonb | SÍ | {} | Estado actual del bot (modo, vacante_id, etc.) |
| `updated_at` | timestamptz | SÍ | now() | — |

---

## candidatos

Tabla central del funnel RH. Un registro por candidato por vacante.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `vacante_id` | uuid | SÍ | — | FK → vacantes.id |
| `nombre` | text | SÍ | — | Nombre capturado en el formulario |
| `telefono` | text | SÍ | — | Teléfono |
| `email` | text | SÍ | — | Email |
| `canal` | text | NO | — | Canal de entrada (telegram, whatsapp, instagram…) |
| `canal_user_id` | text | NO | — | ID externo del usuario en la plataforma |
| `estado` | text | NO | 'nuevo' | Estado en pipeline (nuevo, apto, no_apto, contratado…) |
| `duplicado_de` | uuid | SÍ | — | FK → candidatos.id si es duplicado |
| `folio` | text | SÍ | — | Folio legible (CAND-001) |
| `created_at` | timestamptz | SÍ | now() | — |

> **Nota IDs**: `canal_user_id` es el ID externo de la plataforma (ej. Telegram user ID). `id` es el UUID interno usado por todos los demás skills.

---

## conversaciones

Estado de la conversación activa entre un candidato y una vacante.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `candidato_id` | uuid | SÍ | — | FK → candidatos.id |
| `vacante_id` | uuid | SÍ | — | FK → vacantes.id |
| `canal` | text | NO | — | Canal activo |
| `estado` | text | NO | 'sin_flujo' | Estado (iniciando, haciendo_cuestionario, finalizado…) |
| `cuestionario_paso` | integer | SÍ | 0 | Último paso respondido |
| `datos_temp` | jsonb | SÍ | — | Datos temporales del flujo |
| `created_at` | timestamptz | SÍ | now() | — |
| `updated_at` | timestamptz | SÍ | now() | — |

---

## cuestionarios

Cuestionarios generados por vacante. Un cuestionario por vacante y profundidad.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `empresa_id` | text | NO | — | ID de empresa |
| `vacante_id` | uuid | SÍ | — | FK → vacantes.id |
| `puesto` | text | NO | — | Nombre del puesto |
| `profundidad` | text | NO | 'simple' | simple, medio, robusto, custom |
| `canal` | text | SÍ | — | Canal para el que fue generado |
| `preguntas` | jsonb | NO | — | Array de preguntas [{pregunta, orden}] |
| `created_at` | timestamptz | SÍ | now() | — |

---

## eventos_historial

Log inmutable de eventos por candidato.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `candidato_id` | uuid | NO | — | FK → candidatos.id |
| `tipo_evento` | text | NO | — | Tipo (pipeline_cambiado, score_generado…) |
| `datos` | jsonb | SÍ | — | Payload del evento |
| `created_at` | timestamptz | SÍ | now() | — |

---

## fb_grupos

Grupos de Facebook descubiertos vía `facebook_group_finder`.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `url` | text | NO | — | URL del grupo (único) |
| `slug` | text | SÍ | — | Slug del grupo |
| `nombre` | text | SÍ | — | Nombre del grupo |
| `descripcion` | text | SÍ | — | Descripción pública |
| `region` | text | SÍ | — | Región geográfica |
| `vertical` | text | SÍ | — | Vertical que lo usa (tractohub…) |
| `activo` | boolean | SÍ | true | Si está activo para publicar |
| `created_at` | timestamptz | SÍ | now() | — |

---

## fb_publicaciones

Registro de cada post publicado o intentado en un grupo de Facebook.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `vacante_id` | uuid | SÍ | — | FK → vacantes.id |
| `empresa_id` | text | SÍ | — | ID de empresa |
| `grupo_url` | text | NO | — | URL del grupo |
| `grupo_nombre` | text | SÍ | — | Nombre del grupo |
| `texto` | text | SÍ | — | Texto publicado (primeros 500 chars) |
| `publicado` | boolean | SÍ | false | Si se publicó realmente |
| `dry_run` | boolean | SÍ | true | Si fue simulación |
| `fecha` | timestamptz | SÍ | — | Fecha de publicación |
| `created_at` | timestamptz | SÍ | now() | — |

---

## mensajes

Mensajes dentro de una conversación (historial de chat).

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `conversacion_id` | uuid | NO | — | FK → conversaciones.id |
| `rol` | text | NO | — | user \| assistant |
| `contenido` | text | NO | — | Texto del mensaje |
| `created_at` | timestamptz | SÍ | now() | — |

---

## onboarding_docs

Documentos recopilados por candidato en el flow de onboarding de TractHub.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `candidato_id` | uuid | NO | — | FK → candidatos.id (UUID interno) |
| `empresa_id` | text | SÍ | — | ID de empresa |
| `doc_clave` | text | NO | — | Clave del doc (ine_frente, licencia_federal…) |
| `doc_nombre` | text | SÍ | — | Nombre legible |
| `estado` | text | SÍ | 'pendiente' | pendiente \| recibido |
| `file_id` | text | SÍ | — | file_id de Telegram (para fotos/docs) |
| `valor_texto` | text | SÍ | — | Valor para campos de texto (ej. IMSS) |
| `fecha` | timestamptz | SÍ | — | Fecha de recepción |
| `created_at` | timestamptz | SÍ | now() | — |

---

## pipeline

Historial de movimientos de etapa por candidato.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `candidato_id` | uuid | NO | — | FK → candidatos.id |
| `vacante_id` | uuid | NO | — | FK → vacantes.id |
| `etapa` | text | NO | — | nuevo, apto, no_apto, listo_entrevista, contratado… |
| `notas` | text | SÍ | — | Notas del movimiento |
| `created_at` | timestamptz | SÍ | now() | — |
| `updated_at` | timestamptz | SÍ | now() | — |

---

## respuestas

Respuestas del candidato al cuestionario, una fila por pregunta.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `candidato_id` | uuid | NO | — | FK → candidatos.id |
| `vacante_id` | uuid | NO | — | FK → vacantes.id |
| `pregunta` | text | NO | — | Texto de la pregunta |
| `respuesta` | text | SÍ | — | Respuesta del candidato |
| `orden` | integer | SÍ | — | Número de pregunta en el cuestionario |
| `created_at` | timestamptz | SÍ | now() | — |

---

## scores

Puntuación generada por IA por candidato y vacante.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `candidato_id` | uuid | NO | — | FK → candidatos.id |
| `vacante_id` | uuid | NO | — | FK → vacantes.id |
| `score_total` | numeric | SÍ | — | Puntaje 0-100 |
| `pasa_knockout` | boolean | SÍ | — | Si cumple requisitos obligatorios |
| `detalle` | jsonb | SÍ | — | Desglose por criterio + resumen IA |
| `created_at` | timestamptz | SÍ | now() | — |

---

## test_seeds

Registro de IDs creados por seeds de prueba para poder limpiarlos.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `seed_label` | text | NO | — | Etiqueta del seed (seed_20250506_130000) |
| `empresa_id` | text | NO | — | ID de empresa del seed |
| `tabla` | text | NO | — | Nombre de la tabla donde se insertó |
| `registro_id` | uuid | NO | — | ID del registro creado |
| `created_at` | timestamptz | SÍ | now() | — |

---

## vacantes

Vacantes activas por empresa. Tabla de origen del funnel.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `empresa_id` | text | NO | — | ID de empresa |
| `titulo` | text | NO | — | Título del puesto |
| `descripcion` | text | SÍ | — | Descripción del puesto |
| `requisitos` | jsonb | SÍ | — | Requisitos estructurados |
| `canal` | text | SÍ | — | Canal principal de publicación |
| `estado` | text | NO | 'activa' | activa \| pausada \| cerrada |
| `folio` | text | SÍ | — | Folio legible (VAC-001) |
| `tipo` | text | SÍ | 'real' | real \| seed |
| `created_at` | timestamptz | SÍ | now() | — |

---

## entrevistas

Entrevistas agendadas por candidato y reclutador. Usada por `rh_interview_scheduler`.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `candidato_id` | uuid | NO | — | FK → candidatos.id |
| `reclutador_id` | uuid | SÍ | — | FK → reclutadores.id |
| `vacante_id` | uuid | SÍ | — | FK → vacantes.id |
| `fecha_hora` | text | NO | — | Fecha y hora de la entrevista (YYYY-MM-DD HH:MM) |
| `duracion_min` | integer | SÍ | 30 | Duración en minutos |
| `tipo` | text | NO | 'presencial' | presencial \| videollamada \| telefonica |
| `estado` | text | NO | 'agendada' | agendada \| cancelada \| realizada |
| `notas` | text | SÍ | — | Notas adicionales |
| `created_at` | timestamptz | SÍ | now() | — |

---

## reclutadores

Reclutadores disponibles para asignación de candidatos calificados. Usada por `rh_recruiter_router`.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `nombre` | text | NO | — | Nombre del reclutador |
| `telegram_chat_id` | text | SÍ | — | Chat ID de Telegram para notificaciones |
| `empresa_id` | text | SÍ | — | Empresa a la que está asignado |
| `zona` | text | SÍ | — | Zona geográfica de cobertura |
| `activo` | boolean | SÍ | true | Si está disponible para recibir candidatos |
| `created_at` | timestamptz | SÍ | now() | — |

---

## whatsapp_broadcasts

Broadcasts enviados o programados por WhatsApp vía `whatsapp_group_broadcaster`.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `destino` | text | SÍ | — | Número de teléfono destino (+521…) |
| `texto` | text | SÍ | — | Texto enviado |
| `enviado` | boolean | SÍ | false | Si fue enviado exitosamente |
| `backend` | text | SÍ | — | twilio \| meta \| playwright \| dry_run |
| `vacante_id` | uuid | SÍ | — | FK → vacantes.id |
| `empresa_id` | text | SÍ | — | ID de empresa |
| `fecha` | timestamptz | SÍ | — | Fecha de envío |
| `error` | text | SÍ | — | Error si falló |
| `created_at` | timestamptz | SÍ | now() | — |