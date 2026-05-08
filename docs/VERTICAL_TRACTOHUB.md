# vertical_tractohub

Plataforma de IA para reclutamiento de operadores de transporte de carga (tractocamionistas).
Canal de entrada: grupos de Facebook → Telegram bot → pipeline RH automatico.

## Naming convention

- Skills genéricos Facebook: `facebook_xxx`
- Skills genéricos RH reutilizables: `rh_xxx`
- Skills específicos TractHub: `tractohub_xxx`

## Flujo completo

```
[Setup]
crear_vacante → rh_vacante_store + rh_questionnaire_generator

[Facebook]
buscar_grupos → facebook_group_finder (Google scraping → fb_grupos)
              → facebook_post_generator (variantes con IA)
              → facebook_post_publisher (Playwright, 1 grupo por llamada)
              → facebook_post_tracker (registra en fb_publicaciones, cooldown 72h)

[Candidato llega por Telegram]
mensaje_entrante → bot_inbox_router
                → bot_form_capture (cuestionario paso a paso)
                → [completado] rh_post_score_orchestrator
                    → rh_candidate_profile_builder
                    → rh_basic_validation
                    → rh_duplicate_detector
                    → rh_knockout_filter
                    → rh_candidate_scoring
                    → rh_pipeline_manager
                    → telegram_send_message (notifica manager)

[Gestión]
rh_candidate_ranking / rh_report_generator / rh_candidate_history
```

## Skills

| # | Skill | Tipo | Estado | Necesita |
|---|---|---|---|---|
| 1 | `facebook_group_finder` | Genérico | ✅ Listo | — |
| 2 | `facebook_post_generator` | Genérico | ✅ Listo | ANTHROPIC_API_KEY |
| 3 | `facebook_post_publisher` | Genérico | ✅ Listo (dry_run) | FB_EMAIL + FB_PASSWORD + Playwright |
| 4 | `facebook_post_tracker` | Genérico | ✅ Listo | Tabla fb_publicaciones en Supabase |
| 5 | `rh_post_score_orchestrator` | Genérico RH | ✅ Listo | MANAGER_TELEGRAM_CHAT_ID |
| 6 | `tractohub_rh_1` | Orquestador | ✅ Listo | TRACTOHUB_EMPRESA_ID, TRACTOHUB_CONTACTO |
| 7 | `bot_inbox_router` | Existente | ✅ | — |
| 8 | `bot_form_capture` | Existente | ✅ | — |
| 9 | `rh_vacante_store` | Existente | ✅ | — |
| 10 | `rh_questionnaire_generator` | Existente | ✅ | — |
| 11 | `rh_candidate_profile_builder` | Existente | ✅ | — |
| 12 | `rh_basic_validation` | Existente | ✅ | — |
| 13 | `rh_duplicate_detector` | Existente | ✅ | — |
| 14 | `rh_knockout_filter` | Existente | ✅ | — |
| 15 | `rh_candidate_scoring` | Existente | ✅ | — |
| 16 | `rh_pipeline_manager` | Existente | ✅ | — |
| 17 | `rh_candidate_ranking` | Existente | ✅ | — |
| 18 | `rh_report_generator` | Existente | ✅ | — |
| 19 | `telegram_send_message` | Existente | ✅ | FACTORY3_ADMIN_BOT_TOKEN |
| 20 | `facebook_marketplace_poster` | Genérico | ✅ Listo (dry_run) | FB_EMAIL + FB_PASSWORD + Playwright |
| 21 | `whatsapp_group_broadcaster` | Genérico | ✅ Listo (dry_run) | WA_BACKEND=twilio\|meta cuando tengas cuenta |
| 22 | `tractohub_driver_onboarding` | TractHub | ✅ Listo | Tabla onboarding_docs en Supabase |

## Variables de entorno requeridas

```
TRACTOHUB_EMPRESA_ID=tractohub
TRACTOHUB_REGION=peninsula de yucatan mexico
TRACTOHUB_CONTACTO=https://t.me/tu_bot
MANAGER_TELEGRAM_CHAT_ID=123456789
FB_EMAIL=cuenta@empresa.com          # cuando actives Playwright
FB_PASSWORD=password                 # cuando actives Playwright
```

## Tablas Supabase nuevas

- `fb_grupos` — grupos descubiertos (url, slug, nombre, descripcion, region, vertical, activo)
- `fb_publicaciones` — registro de publicaciones (vacante_id, empresa_id, grupo_url, texto, publicado, dry_run, fecha)
- `whatsapp_broadcasts` — broadcasts WA (destino, texto, enviado, backend, vacante_id, empresa_id, fecha, error)
- `onboarding_docs` — documentos por candidato (candidato_id, empresa_id, doc_clave, doc_nombre, estado, file_id, valor_texto, fecha)

## Uso desde CLI

```bash
# Buscar grupos
python main.py run-skill tractohub_rh_1 --context '{"comando":"buscar_grupos"}'

# Publicar vacante en un grupo (dry_run)
python main.py run-skill tractohub_rh_1 --context '{"comando":"publicar_vacante","vacante_id":"xxx","grupo_url":"https://facebook.com/groups/yyy","dry_run":true}'

# Crear vacante completa
python main.py run-skill tractohub_rh_1 --context '{"comando":"crear_vacante","titulo":"Operador de tractocamion","descripcion":"...","requisitos":"...","salario":"$18,000 - $22,000"}'
```

## Historial de cambios

| Fecha | Cambio |
|---|---|
| 2026-05-06 | Vertical creada |
| 2026-05-06 | 6 skills nuevos: facebook_group_finder, facebook_post_generator, facebook_post_publisher, facebook_post_tracker, rh_post_score_orchestrator, tractohub_rh_1 |
| 2026-05-06 | 3 skills nuevos: facebook_marketplace_poster, whatsapp_group_broadcaster, tractohub_driver_onboarding |
