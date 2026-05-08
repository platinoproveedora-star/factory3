# mass_digital_hiring_run

Orquestador master genérico para contratación masiva digital. Multi-cliente: toda la config viene por context o env vars. Cubre el flujo completo de inicio a fin.

## Comandos

| comando | qué hace |
|---|---|
| `crear_vacante` | Crea vacante + cuestionario + QR de entrada |
| `planificar_campana` | demand_planner + offer_builder + ad_copy_generator |
| `lanzar_campana` | Publica en Facebook / WhatsApp / Telegram |
| `buscar_grupos` | Busca grupos FB por keywords y región |
| `publicar_vacante` | Publica en un grupo FB específico con cooldown |
| `mensaje_entrante` | Procesa mensaje de candidato vía bot |
| `distribuir` | Reparte candidatos aptos entre empresas/contratistas |
| `status` | KPIs generales del sistema |

## Config por context o env var

| context key | env var | descripción |
|---|---|---|
| `empresa_id` | `MDH_EMPRESA_ID` | ID de la empresa cliente |
| `region` | `MDH_REGION` | Región geográfica |
| `bot_url` | `MDH_BOT_URL` | URL del bot de captura |
| `contacto` | `MDH_CONTACTO` | Link o teléfono de contacto |
| `manager_chat_id` | `MANAGER_TELEGRAM_CHAT_ID` | Chat ID del manager para notificaciones |
| `telegram_token` | `FACTORY3_ADMIN_BOT_TOKEN` | Token del bot Telegram |

## Flujo completo

```
crear_vacante
    ↓
planificar_campana  (demanda + oferta + copy)
    ↓
buscar_grupos  →  lanzar_campana / publicar_vacante
    ↓
mensaje_entrante  (bot_form_capture → rh_post_score_orchestrator)
    ↓ (auto si auto_route_recruiter=true)
rh_recruiter_router
    ↓ (manual)
distribuir
```

## Diferencia con tractohub_rh_1

`tractohub_rh_1` está hardcodeado a un cliente (Yucatán, choferes, keywords específicas).
`mass_digital_hiring_run` es genérico: cualquier puesto, región, empresa y canales.

## Opciones especiales

| campo | tipo | descripción |
|---|---|---|
| `auto_route_recruiter` | bool | Si `true`, después del score dispara `rh_recruiter_router` automáticamente |
| `onboarding_skill` | str | Nombre del skill de onboarding a usar (ej: `tractohub_driver_onboarding`) |
| `dry_run` | bool | `true` = simular sin publicar ni escribir |
