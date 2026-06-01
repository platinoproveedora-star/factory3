# Tablas Supabase — Registry

Actualizado: 2026-05-15

## Schema `public`

| Tabla | Vertical | Descripción |
|---|---|---|
| [agent_memory](#agent_memory) | factory | Memoria persistente de agentes |
| [bot_states](#bot_states) | factory | Estado de sesión por chat_id de Telegram |
| [factory_tasks](#factory_tasks) | factory | Cola de tareas asíncronas del runtime |
| [test_seeds](#test_seeds) | factory | Registro de IDs generados por seeds de prueba |
| [candidatos](#candidatos) | rh | Candidatos registrados — tabla central del funnel |
| [vacantes](#vacantes) | rh | Vacantes activas por empresa |
| [pipeline](#pipeline) | rh | Historial de etapas por candidato |
| [conversaciones](#conversaciones) | rh | Estado de conversación activa por candidato y vacante |
| [mensajes](#mensajes) | rh | Mensajes dentro de una conversación |
| [cuestionarios](#cuestionarios) | rh | Cuestionarios generados por vacante |
| [respuestas](#respuestas) | rh | Respuestas del candidato al cuestionario |
| [scores](#scores) | rh | Puntuación y resultado knockout por candidato |
| [entrevistas](#entrevistas) | rh | Entrevistas agendadas por candidato y reclutador |
| [reclutadores](#reclutadores) | rh | Reclutadores activos para asignación de candidatos |
| [alertas](#alertas) | rh | Alertas enviadas a candidatos |
| [eventos_historial](#eventos_historial) | rh | Log de eventos por candidato |
| [onboarding_docs](#onboarding_docs) | tractohub | Documentos recopilados en onboarding de operador |
| [fb_grupos](#fb_grupos) | social | Grupos de Facebook descubiertos para publicar |
| [fb_gs_searches](#fb_gs_searches) | social | Búsquedas de grupos FB vía Google Search |
| [fb_gs_groups](#fb_gs_groups) | social | Grupos encontrados por búsqueda FB-GS |
| [fb_publicaciones](#fb_publicaciones) | social | Registro de posts publicados en grupos FB |
| [whatsapp_broadcasts](#whatsapp_broadcasts) | social | Broadcasts enviados o programados por WhatsApp |
| [cfdi_documentos](#cfdi_documentos) | fiscal | Documentos CFDI timbrados (facturas, notas) |
| [wabiz_config](#wabiz_config) | vertical_wabiz | Credenciales WhatsApp Business por empresa_id |
| [wabiz_messages](#wabiz_messages) | vertical_wabiz | Log de mensajes WhatsApp entrantes y salientes |
| [factory_users](#factory_users) | factory | Usuarios globales de la fábrica (todos los canales) |
| [wabiz_access_codes](#wabiz_access_codes) | vertical_wabiz | Claves de registro de usuarios vía WhatsApp |

## Schema `estoikolab`

| Tabla | Descripción |
|---|---|
| [estoikolab.chat_leads](#estoikolabchat_leads) | Leads capturados por agentes de chat. Folio LEAD-001… |

## Schema `logplat`

| Tabla | Descripción |
|---|---|
| [logplat.viajes](#logplatviajes) | Viajes de transporte. Folio VIA-001… |
| [logplat.gastos](#logplatgastos) | Gastos operativos por viaje. Folio GAS-001… |
| [logplat.pagos](#logplatpagos) | Pagos recibidos de clientes. Folio PAG-001… |
| [logplat.cuentas_por_cobrar](#logplatcuentas_por_cobrar) | CXC derivada de viajes. Folio CXC-001… |
| [logplat.viaje_docs](#logplatviaje_docs) | Documentos adjuntos a viajes. Folio DOC-001… |

## Schema `uc101_proy001` — EMP_DURALON / PROY-001 / gastos

ERP-ready: todas las tablas tienen `empresa_id`, `project_code`, `module_code`.

| Tabla | Descripción |
|---|---|
| `uc101_proy001.usuarios` | Usuarios del bot. Folio USR-001… Columnas: telegram_chat_id, rol, modules_allowed, global_user_id |
| `uc101_proy001.categorias_gasto` | Catálogo de 12 categorías de gasto (combustible, nomina, etc.) |
| `uc101_proy001.gastos` | Gastos registrados. Folio GAS-001… Campos ERP: cost_center_id, customer_id, supplier_id, erp_tags |
| `uc101_proy001.gasto_documentos` | Fotos/tickets adjuntos a gastos. Folio DOC-001… URL en Supabase Storage |
| `uc101_proy001.gasto_eventos` | Auditoría de cambios por gasto y usuario |

## Schema `freelance`

| Tabla | Descripcion |
|---|---|
| [freelance.jobs](#freelancejobs) | Vacantes pegadas/analizadas para Upwork y otros canales. |
| [freelance.proposals](#freelanceproposals) | Propuestas generadas para vacantes freelance. |
| [freelance.tasks](#freelancetasks) | Checklist operativo del registro, portafolio y seguimiento. |
| [freelance.assets](#freelanceassets) | Assets de portafolio por proyecto: screenshots, videos, links. |

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

Estado de sesión del bot por chat. Persiste el `state` entre mensajes de Telegram y WhatsApp.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `chat_id` | text | NO | — | ID único del chat. Telegram: chat_id numérico. WhatsApp: `wabiz_{empresa_id}_{phone}` |
| `state` | jsonb | SÍ | {} | Estado actual: modo activo, hint de captura, doc_url pendiente, reg_step… |
| `updated_at` | timestamptz | SÍ | now() | — |

Formato de `chat_id` por canal:

| Canal | Formato | Ejemplo |
|---|---|---|
| Telegram | número plano | `123456789` |
| WhatsApp router | `wabiz_{empresa_id}_{phone}` | `wabiz_factory3_+521234567890` |
| WhatsApp handler logplat | `wabiz_logplat_{phone}` | `wabiz_logplat_+521234567890` |

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

---

## factory_tasks

Cola de tareas asíncronas del runtime factory3. Trazabilidad de ejecuciones de skills.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `task_id` | text | NO | — | ID externo de la tarea |
| `empresa_id` | text | SÍ | — | ID de empresa |
| `skill_name` | text | NO | — | Skill ejecutado |
| `skill_source` | text | SÍ | — | Origen del skill |
| `context` | jsonb | SÍ | — | Contexto de entrada |
| `status` | text | NO | — | pending \| running \| done \| error |
| `resultado` | jsonb | SÍ | — | Resultado de la ejecución |
| `error_msg` | text | SÍ | — | Mensaje de error si falló |
| `prioridad` | integer | SÍ | — | Prioridad de ejecución |
| `parent_task_id` | text | SÍ | — | ID de tarea padre (orquestación) |
| `costo_tokens` | integer | SÍ | — | Tokens consumidos |
| `latencia_ms` | integer | SÍ | — | Latencia de ejecución |
| `created_at` | timestamptz | SÍ | now() | — |
| `started_at` | timestamptz | SÍ | — | — |
| `finished_at` | timestamptz | SÍ | — | — |

---

## fb_gs_searches

Búsquedas de grupos de Facebook ejecutadas vía Google Search.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `search_id` | text | NO | — | ID externo de la búsqueda |
| `empresa_id` | text | SÍ | — | ID de empresa |
| `usuario_id` | text | SÍ | — | Usuario que lanzó la búsqueda |
| `tema_busqueda` | text | SÍ | — | Tema / keyword buscado |
| `fuente` | text | SÍ | — | google_search \| manual |
| `estado` | text | SÍ | — | pendiente \| completado \| error |
| `total_grupos` | integer | SÍ | — | Grupos encontrados |
| `created_at` | timestamptz | SÍ | now() | — |

---

## fb_gs_groups

Grupos encontrados en una búsqueda FB-GS. N filas por `search_id`.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `search_id` | text | NO | — | FK → fb_gs_searches.search_id |
| `empresa_id` | text | SÍ | — | ID de empresa |
| `grupo_nombre` | text | SÍ | — | Nombre del grupo |
| `grupo_url` | text | SÍ | — | URL del grupo |
| `descripcion` | text | SÍ | — | Descripción extraída |
| `miembros_estimados` | integer | SÍ | — | Miembros estimados |
| `ubicacion_detectada` | text | SÍ | — | Ciudad/estado detectado |
| `fuente` | text | SÍ | — | Fuente del dato |
| `created_at` | timestamptz | SÍ | now() | — |

---

## cfdi_documentos

Documentos CFDI timbrados (facturas, notas de crédito). UUID CFDI único.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `uuid_cfdi` | text | NO | — | UUID del CFDI (único) |
| `empresa_id` | text | NO | — | RFC propietario / ID empresa |
| `tipo` | text | SÍ | — | ingreso \| egreso \| traslado |
| `tipo_comprobante` | text | SÍ | — | I \| E \| T \| N \| P |
| `rfc_emisor` | text | SÍ | — | RFC del emisor |
| `nombre_emisor` | text | SÍ | — | Razón social emisor |
| `rfc_receptor` | text | SÍ | — | RFC del receptor |
| `nombre_receptor` | text | SÍ | — | Razón social receptor |
| `fecha_emision` | date | SÍ | — | Fecha del comprobante |
| `fecha_timbrado` | timestamptz | SÍ | — | Fecha de timbrado SAT |
| `total` | numeric | SÍ | — | Total del CFDI |
| `subtotal` | numeric | SÍ | — | Subtotal |
| `descuento` | numeric | SÍ | — | Descuento aplicado |
| `moneda` | text | SÍ | 'MXN' | Moneda |
| `metodo_pago` | text | SÍ | — | PUE \| PPD |
| `forma_pago` | text | SÍ | — | 01 efectivo, 03 transferencia… |
| `uso_cfdi` | text | SÍ | — | Clave de uso (G01, G03…) |
| `estado` | text | SÍ | — | vigente \| cancelado |
| `conceptos` | jsonb | SÍ | — | Array de conceptos del CFDI |
| `xml_raw` | text | SÍ | — | XML completo del CFDI |
| `created_at` | timestamptz | SÍ | now() | — |

---

## logplat.viajes

Schema: `logplat` | Empresa: LOGPLAT — Platino Logística

Viajes de transporte. Tabla central de la vertical logplat.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `folio` | text | NO | — | Folio visible VIA-001… |
| `empresa_id` | text | NO | 'LOGPLAT' | ID de empresa |
| `cliente` | text | SÍ | — | Cliente del viaje |
| `origen` | text | SÍ | — | Ciudad/punto de origen |
| `destino` | text | SÍ | — | Ciudad/punto de destino |
| `fecha_salida` | date | SÍ | — | Fecha de salida |
| `fecha_llegada` | date | SÍ | — | Fecha de llegada |
| `chofer` | text | SÍ | — | Nombre del chofer |
| `costo_viaje` | numeric | SÍ | 0 | Suma de gastos (calculado) |
| `precio_venta_viaje` | numeric | SÍ | 0 | Precio cobrado al cliente |
| `utilidad_viaje` | numeric | SÍ | 0 | precio_venta − costo (calculado) |
| `estatus_viaje` | text | SÍ | 'activo' | activo \| terminado \| cancelado |
| `estatus_pago` | text | SÍ | 'por_cobrar' | por_cobrar \| parcial \| pagado |
| `id_doc` | text | SÍ | — | URL legacy de doc único (ver viaje_docs) |
| `created_at` | timestamptz | SÍ | now() | — |
| `updated_at` | timestamptz | SÍ | now() | — |

---

## logplat.gastos

Schema: `logplat` | Empresa: LOGPLAT

Gastos operativos por viaje (diesel, casetas, pensiones, etc.).

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `folio` | text | NO | — | Folio visible GAS-001… |
| `empresa_id` | text | NO | 'LOGPLAT' | ID de empresa |
| `numero_viaje` | text | SÍ | — | FK → viajes.folio |
| `fecha_gasto` | date | SÍ | — | Fecha del gasto |
| `fecha_captura` | timestamptz | SÍ | — | Fecha de captura en sistema |
| `monto_gasto` | numeric | NO | — | Monto del gasto |
| `concepto` | text | SÍ | — | Descripción del gasto |
| `chofer` | text | SÍ | — | Chofer que generó el gasto |
| `tipo_gasto` | text | SÍ | 'otro' | diesel \| caseta \| pension \| otro |
| `id_doc` | text | SÍ | — | URL del comprobante en Storage |
| `created_at` | timestamptz | SÍ | now() | — |
| `updated_at` | timestamptz | SÍ | now() | — |

---

## logplat.pagos

Schema: `logplat` | Empresa: LOGPLAT

Pagos recibidos de clientes por viaje.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `folio` | text | NO | — | Folio visible PAG-001… |
| `empresa_id` | text | NO | 'LOGPLAT' | ID de empresa |
| `numero_viaje` | text | SÍ | — | FK → viajes.folio |
| `cliente` | text | SÍ | — | Cliente que pagó |
| `fecha_pago` | date | SÍ | — | Fecha del pago |
| `monto_pago` | numeric | NO | — | Monto recibido |
| `metodo_pago` | text | SÍ | 'transferencia' | transferencia \| efectivo \| cheque |
| `observaciones` | text | SÍ | — | Notas del pago |
| `id_doc` | text | SÍ | — | URL del comprobante en Storage |
| `created_at` | timestamptz | SÍ | now() | — |
| `updated_at` | timestamptz | SÍ | now() | — |

---

## logplat.cuentas_por_cobrar

Schema: `logplat` | Empresa: LOGPLAT

CXC derivada automáticamente al crear un viaje con `estatus_pago=por_cobrar`. Read-only en dashboard.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `folio` | text | NO | — | Folio visible CXC-001… |
| `empresa_id` | text | NO | 'LOGPLAT' | ID de empresa |
| `numero_viaje` | text | NO | — | FK → viajes.folio |
| `cliente` | text | SÍ | — | Cliente |
| `monto_total` | numeric | SÍ | 0 | Total a cobrar |
| `monto_pagado` | numeric | SÍ | 0 | Total pagado acumulado |
| `saldo_pendiente` | numeric | SÍ | 0 | monto_total − monto_pagado |
| `fecha_viaje` | date | SÍ | — | Fecha del viaje asociado |
| `fecha_vencimiento` | date | SÍ | — | Fecha límite de pago |
| `estatus_cobro` | text | SÍ | 'pendiente' | pendiente \| parcial \| pagado |
| `created_at` | timestamptz | SÍ | now() | — |
| `updated_at` | timestamptz | SÍ | now() | — |

---

## logplat.viaje_docs

Schema: `logplat` | Empresa: LOGPLAT

Documentos adjuntos a viajes (cartas porte, permisos, etc.). N documentos por viaje.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `folio` | text | NO | — | Folio visible DOC-001… |
| `viaje_folio` | text | NO | — | FK → viajes.folio |
| `doc_url` | text | NO | — | URL pública en Supabase Storage |
| `tipo` | text | NO | 'otro' | carta_porte \| permiso \| otro |
| `nombre` | text | SÍ | — | Nombre original del archivo |
| `created_at` | timestamptz | SÍ | now() | — |

---

## freelance.jobs

Schema: `freelance` | Empresa: EMP_FREELANCE_GROWTH

Vacantes freelance copiadas desde Upwork u otros canales y analizadas por `vertical_freelance_growth/upwork_job_matcher`.

| Campo | Tipo | Nulo | Default | Descripcion |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `company_id` | text | NO | 'EMP_FREELANCE_GROWTH' | Empresa dueña del flujo |
| `source` | text | NO | 'upwork' | Canal de origen |
| `job_text` | text | NO | — | Texto completo de la vacante |
| `score` | integer | SI | — | Score 0-100 calculado por el matcher |
| `decision` | text | SI | — | apply_now, apply_if_budget_ok, skip_or_low_priority |
| `decision_es` | text | SI | — | Decision legible en espanol |
| `matched_terms` | jsonb | NO | [] | Terminos detectados a favor |
| `risk_terms` | jsonb | NO | [] | Terminos o señales de riesgo |
| `relevant_projects` | jsonb | NO | [] | Proyectos del portafolio relacionados |
| `strengths` | jsonb | NO | [] | Fortalezas para aplicar |
| `risks` | jsonb | NO | [] | Riesgos antes de aplicar |
| `proposal_angle` | text | SI | — | Angulo sugerido para la propuesta |
| `saved_file` | text | SI | — | Archivo local generado como respaldo |
| `status` | text | NO | 'analyzed' | analyzed, applied, won, lost, archived |
| `created_at` | timestamptz | NO | now() | — |
| `updated_at` | timestamptz | NO | now() | — |

---

## freelance.proposals

Schema: `freelance` | Empresa: EMP_FREELANCE_GROWTH

Propuestas generadas por `vertical_freelance_growth/upwork_proposal_generator`.

| Campo | Tipo | Nulo | Default | Descripcion |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `company_id` | text | NO | 'EMP_FREELANCE_GROWTH' | Empresa dueña del flujo |
| `source` | text | NO | 'upwork' | Canal de origen |
| `job_id` | uuid | SI | — | FK opcional a freelance.jobs.id |
| `job_text` | text | SI | — | Texto de la vacante usada |
| `proposal_text` | text | NO | — | Propuesta lista para copiar |
| `matched_projects` | jsonb | NO | [] | Proyectos usados como prueba |
| `saved_file` | text | SI | — | Archivo local generado como respaldo |
| `status` | text | NO | 'draft' | draft, sent, won, lost, archived |
| `created_at` | timestamptz | NO | now() | — |
| `updated_at` | timestamptz | NO | now() | — |

---

## freelance.tasks

Schema: `freelance` | Empresa: EMP_FREELANCE_GROWTH

Checklist operativo del proceso freelance: registro, portafolio, screenshots, aplicaciones y seguimiento.

| Campo | Tipo | Nulo | Default | Descripcion |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `company_id` | text | NO | 'EMP_FREELANCE_GROWTH' | Empresa dueña del flujo |
| `area` | text | NO | 'upwork_registration' | Area operativa |
| `title` | text | NO | — | Tarea |
| `done` | boolean | NO | false | Si ya se completo |
| `notes` | text | SI | — | Notas |
| `created_at` | timestamptz | NO | now() | — |
| `updated_at` | timestamptz | NO | now() | — |

---

## freelance.assets

Schema: `freelance` | Empresa: EMP_FREELANCE_GROWTH

Assets asociados al portafolio freelance: screenshots, videos, links publicos y notas por proyecto.

| Campo | Tipo | Nulo | Default | Descripcion |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `company_id` | text | NO | 'EMP_FREELANCE_GROWTH' | Empresa dueña del flujo |
| `project_id` | text | NO | — | ID del proyecto en projects.json |
| `asset_type` | text | NO | — | screenshot, video, link, doc |
| `title` | text | SI | — | Nombre legible del asset |
| `url` | text | SI | — | URL publica o privada |
| `notes` | text | SI | — | Notas del asset |
| `created_at` | timestamptz | NO | now() | — |

---

## factory_users

Vertical: `factory` | Schema: `public`

Usuarios globales de la fábrica. Todos los canales (WhatsApp, Telegram, futuro) referencian esta tabla.
Se crea automáticamente cuando el usuario se registra vía WhatsApp con un código de acceso.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `nombre` | text | NO | — | Nombre del usuario |
| `empresa_id` | text | NO | — | Empresa a la que pertenece (logplat, rh…) |
| `role` | text | NO | 'user' | chofer, admin, reclutador… |
| `user_mode` | text[] | NO | '{}' | Modos permitidos: ["logplat"], ["logplat","rh"] |
| `phone` | text | SÍ | — | UNIQUE — número WhatsApp (+521…) |
| `telegram_id` | text | SÍ | — | UNIQUE — chat_id de Telegram |
| `activo` | boolean | NO | true | Si el usuario está habilitado |
| `created_at` | timestamptz | NO | now() | — |

---

## wabiz_access_codes

Vertical: `vertical_wabiz` | Schema: `public`

Claves de acceso para auto-registro de usuarios vía WhatsApp.
El admin crea claves; cada clave define qué empresa y modos tendrá el usuario que la use.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `codigo` | text | NO | — | PK — clave que escribe el usuario (ej: logplat26) |
| `empresa_id` | text | NO | — | Empresa que se asigna al registrarse |
| `user_mode` | text[] | NO | '{}' | Modos permitidos para el usuario nuevo |
| `role` | text | NO | 'user' | Rol que se asigna (chofer, admin…) |
| `activo` | boolean | NO | true | Si la clave está habilitada |
| `created_at` | timestamptz | NO | now() | — |

Claves activas:

| Código | empresa_id | user_mode | role |
|---|---|---|---|
| `logplat26` | logplat | ["logplat"] | chofer |
| `admin2026` | logplat | ["logplat"] | admin |

---

## wabiz_config

Vertical: `vertical_wabiz` | Schema: `public`

Credenciales y configuración WhatsApp Business Cloud API por empresa. Una fila por empresa_id.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `empresa_id` | text | NO | — | UNIQUE — identificador de empresa |
| `phone_number_id` | text | NO | — | ID del número en Meta (WABA) |
| `business_account_id` | text | NO | '' | WhatsApp Business Account ID |
| `access_token` | text | NO | — | Token de acceso permanente Meta |
| `verify_token` | text | NO | — | Token secreto para verificación de webhook |
| `graph_version` | text | NO | 'v24.0' | Versión Graph API a usar |
| `created_at` | timestamptz | NO | now() | — |
| `updated_at` | timestamptz | NO | now() | Se actualiza en cada upsert |

---

## wabiz_messages

Vertical: `vertical_wabiz` | Schema: `public`

Log de todos los mensajes WhatsApp entrantes y salientes por empresa. Sirve como memoria de conversación para el router de IA.

| Campo | Tipo | Nulo | Default | Descripción |
|---|---|---|---|---|
| `id` | uuid | NO | gen_random_uuid() | PK interno |
| `empresa_id` | text | NO | — | Empresa dueña del número |
| `from_phone` | text | NO | — | Número del usuario (dirección in) o destino (out) |
| `direction` | text | NO | — | `in` (recibido) o `out` (enviado) |
| `type` | text | NO | 'text' | text, image, audio, video, document, location… |
| `body` | text | SÍ | — | Texto del mensaje o media_id si es archivo |
| `wa_message_id` | text | SÍ | — | ID de mensaje Meta (para dedup y status tracking) |
| `timestamp` | timestamptz | NO | now() | Timestamp original del evento Meta |

Índice: `(empresa_id, from_phone, timestamp DESC)` para cargar historial de conversación.
