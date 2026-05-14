# vertical_wabiz

Canal WhatsApp Business Cloud API integrado al core de la fábrica.
Multiempresa: cada empresa tiene su propio `phone_number_id` y credenciales en `wabiz_config`.

## Flujo Fase 1 (conexión + webhook)

```
wabiz_store_config          ← guarda credenciales por empresa_id
-> wabiz_connection_check   ← valida token contra Graph API
-> GET /wabiz/{empresa_id}  ← Meta verifica webhook (hub.challenge)
-> POST /wabiz/{empresa_id} ← Meta envía eventos
   -> wabiz_webhook_parse   ← normaliza evento al formato interno
```

## Flujo Fase 2 (envío + IA) — pendiente

```
wabiz_webhook_parse
-> wabiz_channel_router     ← carga config + memoria + Haiku
-> wabiz_send_text          ← envía respuesta al número
```

## Skills

| Skill | Función |
|---|---|
| `vertical_wabiz/wabiz_store_config` | Guarda token, phone_number_id, verify_token por empresa_id |
| `vertical_wabiz/wabiz_connection_check` | Valida token contra Graph API v24.0 |
| `vertical_wabiz/wabiz_webhook_parse` | Normaliza eventos Meta → formato interno, registra en wabiz_messages |
| `vertical_wabiz/wabiz_send_text` | Envía texto vía Cloud API (Fase 2) |
| `vertical_wabiz/wabiz_channel_router` | Orquesta IA: memoria + Haiku + envío (Fase 2) |

## Rutas en factory_api.py

| Método | Ruta | Propósito |
|---|---|---|
| GET | `/wabiz/{empresa_id}` | Verificación webhook Meta (hub.challenge) |
| POST | `/wabiz/{empresa_id}` | Recepción de eventos Meta → wabiz_webhook_parse |

## Tablas Supabase

| Tabla | Descripción |
|---|---|
| `wabiz_config` | Config y credenciales por empresa_id |
| `wabiz_messages` | Log de mensajes in/out (memoria de conversación) |

Ver definición completa en `docs/TABLES.md`.

## Variables de entorno requeridas

```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

Las credenciales WhatsApp (token, phone_number_id, verify_token) se almacenan
en `wabiz_config` por empresa, no como env vars globales.

## Diferencias clave vs Telegram

| Aspecto | Telegram | WhatsApp |
|---|---|---|
| Webhook verify | No aplica | GET con hub.challenge obligatorio |
| Ventana de respuesta | Sin límite | 24h para mensajes libres (Fase 2) |
| Envío | telegram_request() | Graph API POST /messages |
| Media | Descarga directa | Requiere GET media_url primero |

## Pendiente Fase 3 (producción avanzada)

- `wabiz_send_media` — descarga y reenvío de imágenes/audio
- `wabiz_template_sender` — templates oficiales Meta (mensajes fuera ventana 24h)
- `wabiz_24h_window_guard` — control de ventana de conversación
- `wabiz_status_handler` — procesar eventos delivered/read/failed
