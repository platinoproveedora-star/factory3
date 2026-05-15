# vertical_wabiz

Canal WhatsApp Business Cloud API integrado al core de la fábrica.
Un solo número de WhatsApp sirve a todas las empresas y verticales.
El router determina qué handler ejecutar según el usuario registrado.

## Flujo completo

```
POST /wabiz/{empresa_id}         ← Meta envía evento
-> wabiz_webhook_parse           ← normaliza al formato interno
-> wabiz_channel_router          ← verifica usuario, gestiona modo
   -> sin registro               ← flujo de registro (código + nombre)
   -> con registro, 1 modo       ← entra directo al handler
   -> con registro, N modos      ← muestra menú de módulos
   -> emp_logplat_message_handler ← handler LOGPLAT (gastos, viajes, docs)
-> wabiz_send_text               ← envía respuesta
```

## Registro de usuarios

Cuando un número nuevo escribe por primera vez:

```
1. Pide código de acceso
2. Valida contra wabiz_access_codes
3. Pide nombre
4. Crea fila en factory_users con phone + nombre + user_mode del código
5. Si tiene 1 modo → entra directo
6. Si tiene N modos → muestra menú
```

El registro es permanente. El usuario nunca más ingresa código ni elige modo
(a menos que escriba `salir` para cambiar).

## Códigos de acceso activos

| Código | Empresa | Modos | Role |
|---|---|---|---|
| `logplat26` | logplat | ["logplat"] | chofer |
| `admin2026` | logplat | ["logplat"] | admin |

## Comandos globales (cualquier usuario registrado)

| Comando | Acción |
|---|---|
| `ayuda` | Muestra modos disponibles del usuario |
| `salir` | Limpia modo activo, regresa al menú |

## Skills

| Skill | Función |
|---|---|
| `vertical_wabiz/wabiz_store_config` | Guarda token, phone_number_id, verify_token por empresa_id |
| `vertical_wabiz/wabiz_connection_check` | Valida token contra Graph API v24.0 |
| `vertical_wabiz/wabiz_webhook_parse` | Normaliza eventos Meta → formato interno, registra en wabiz_messages |
| `vertical_wabiz/wabiz_send_text` | Envía texto vía Cloud API |
| `vertical_wabiz/wabiz_channel_router` | Router principal: registro, modal, delegación a handler |
| `vertical_wabiz/wabiz_media_downloader` | Descarga media de Meta (imagen, doc, audio) → base64 |
| `emp_logplat_message_handler` | Handler LOGPLAT: gastos, viajes, documentos. Canal-agnostic. |

## Handlers por empresa

Definidos en `wabiz_channel_router/service.py`:

```python
_MODO_HANDLERS = {
    "logplat": "emp_logplat_message_handler",
}
```

Para agregar un handler nuevo: añadir entrada al dict y crear el skill correspondiente.

## emp_logplat_message_handler

Comandos dentro del modo logplat:

| Acción | Formato |
|---|---|
| Registrar gasto (texto) | `gasto` → `cantidad,concepto,dd/mm/yy,viaje` |
| Registrar gasto (foto) | `gasto` → enviar foto del comprobante |
| Registrar viaje (texto) | `viaje` → `numero,origen,destino,precio` |
| Subir doc a viaje | `viaje` → enviar foto/PDF → escribir número de viaje |
| Ayuda logplat | `ayuda` |

El nombre del chofer se toma automáticamente de `factory_users` y se guarda en gastos/viajes.

## Rutas en factory_api.py

| Método | Ruta | Propósito |
|---|---|---|
| GET | `/wabiz/{empresa_id}` | Verificación webhook Meta (hub.challenge) |
| POST | `/wabiz/{empresa_id}` | Recepción de eventos Meta → pipeline completo |

## Tablas Supabase

| Tabla | Descripción |
|---|---|
| `wabiz_config` | Credenciales Meta por empresa_id (token, phone_number_id, verify_token) |
| `wabiz_messages` | Log de mensajes in/out — memoria de conversación |
| `factory_users` | Usuarios registrados con phone, nombre, empresa_id, user_mode |
| `wabiz_access_codes` | Claves de acceso para auto-registro de usuarios |
| `bot_states` | Estado de conversación por chat_id (`wabiz_{empresa_id}_{phone}`) |

Ver definición completa en `docs/TABLES.md`.

## Variables de entorno requeridas

```
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
ANTHROPIC_API_KEY=          ← solo para Haiku genérico (no-logplat)
```

Las credenciales WhatsApp se almacenan en `wabiz_config` por empresa, no como env vars globales.

## Diferencias clave vs Telegram

| Aspecto | Telegram | WhatsApp |
|---|---|---|
| Webhook verify | No aplica | GET con hub.challenge obligatorio |
| Auth usuario | Telegram user_id automático | Registro por código manual |
| Ventana de respuesta | Sin límite | 24h para mensajes libres |
| Media download | Descarga directa | GET media URL con Bearer token primero |
| Estado de sesión | bot_states por chat_id | bot_states por `wabiz_{empresa_id}_{phone}` |

## Pendiente Fase 3 (producción avanzada)

- `wabiz_send_media` — reenvío de imágenes/audio
- `wabiz_template_sender` — templates Meta (fuera ventana 24h)
- `wabiz_24h_window_guard` — control de ventana de conversación
- `wabiz_status_handler` — procesar delivered/read/failed
- Reportes de viajes y gastos desde WhatsApp
- Dashboard: vista de conversación por contacto, métricas reales
