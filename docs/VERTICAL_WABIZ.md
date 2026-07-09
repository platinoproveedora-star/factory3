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
| `vertical_wabiz/wabiz_send_media` | Sube archivo (base64) o referencia link público y lo envía (imagen/doc/audio/video) |
| `vertical_wabiz/wabiz_send_interactive` | Manda botones (máx 3) o lista (máx 10) — respuesta llega como `type=interactive`, `body=id` del botón/fila elegido |
| `vertical_wabiz/wabiz_template_sender` | Envía plantilla Meta pre-aprobada (nombre + params de body) — única forma de escribir fuera de la ventana de 24h |
| `vertical_wabiz/wabiz_24h_window_guard` | Verifica si el último inbound del usuario fue hace menos de 24h; decide texto libre vs plantilla |
| `vertical_wabiz/wabiz_status_handler` | Procesa eventos de status (sent/delivered/read/failed) y actualiza `wabiz_messages` |
| `vertical_wabiz/wabiz_channel_router` | Router principal: registro, modal, delegación a handler |
| `vertical_wabiz/wabiz_media_downloader` | Descarga media de Meta (imagen, doc, audio) → base64 |
| `emp_logplat_message_handler` | Handler LOGPLAT: gastos, viajes, documentos. Canal-agnostic. |
| `vertical_fleet4all_trips/fleet_message_handler` | Handler Fleet4All: viaje, gasto (texto/foto), resumen/KPIs. Canal-agnostic. |

## Handlers por empresa

Definidos en `wabiz_channel_router/service.py`:

```python
_MODO_HANDLERS = {
    "logplat":   "emp_logplat_message_handler",
    "fleet4all": "vertical_fleet4all_trips/fleet_message_handler",
}
```

Nota: el valor debe ser la ruta completa relativa a `skills/internos/` cuando el
handler vive dentro de una carpeta de vertical (ej. `vertical_fleet4all_trips/...`),
porque `_run_handler` arma la ruta de archivo directo a partir de ese string.

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

## Fase 3 (producción avanzada) — estado

- ✅ `wabiz_send_media` — reenvío de imágenes/documentos (código listo, envío real bloqueado por token vencido, ver abajo)
- ✅ `wabiz_template_sender` — templates Meta (fuera ventana 24h) (código listo, mismo bloqueo de token)
- ✅ `wabiz_24h_window_guard` — control de ventana de conversación
- ✅ `wabiz_status_handler` — procesa delivered/read/failed, requiere columnas `status`/`status_updated_at` en `wabiz_messages` (agregadas)
- ✅ Reportes de viajes y gastos desde WhatsApp — comando `resumen`/`kpis` en `fleet_message_handler`, reutiliza `trip_kpis`
- Pendiente: Dashboard con vista de conversación por contacto, métricas reales
- Pendiente: registrar plantillas reales en Meta Business Manager (nombres/textos aprobados) antes de usar `wabiz_template_sender` en producción

## Contrato de respuesta interactiva (botones/listas)

Un handler (ej. `fleet_message_handler`) puede regresar, en vez de `data.reply` (texto),
`data.interactive` con el shape que espera `wabiz_send_interactive`:

```python
{"ok": True, "data": {"interactive": {
    "body": "texto arriba de los botones/lista",
    "interactive_type": "button",  # o "list"
    "buttons": [{"id": "confirmar", "title": "✅ Confirmar"}, ...],   # si es button
    "rows": [{"id": "viaje", "title": "📦 Viaje", "description": "..."}, ...],  # si es list
    "button_label": "Elegir", "section_title": "Fleet4All",           # solo list
}}}
```

`wabiz_channel_router.ejecutar()` revisa `data.interactive` antes que `data.reply` y llama
`wabiz_send_interactive` en vez de `wabiz_send_text`. Cuando el usuario toca un botón o una fila,
Meta lo manda de vuelta como `type=interactive` con `body=<id elegido>` — el router normaliza esto
a `type=text` antes de pasarlo al handler, así que el mismo código que procesa "confirmar" escrito
también procesa el botón "✅ Confirmar" sin cambios.

Nota: la palabra global `ayuda` normalmente la responde el router con el listado genérico de
módulos (`_txt_ayuda`) — si el usuario tiene un solo modo con handler registrado, el router la
delega a ese handler en su lugar, para permitir menús interactivos propios por vertical.

## ⚠️ Bloqueante activo — token vencido

El token del número compartido (`empresa_id=factory3` en `wabiz_config`) expiró el
2026-05-15. Ningún envío saliente (`wabiz_send_text`, `wabiz_send_media`,
`wabiz_template_sender`) funciona hasta generar un token nuevo (idealmente System
User, expiración "Nunca") en Meta Business Manager y actualizarlo vía
`wabiz_store_config`. Los flujos de escritura a Supabase (registro, trips,
expenses, kpis) no se ven afectados — solo la respuesta real por WhatsApp.
