# rh_channel_publisher

Orquesta la publicación de una vacante en Facebook, WhatsApp y/o Telegram en una sola llamada.

## Entradas

| campo | tipo | default | descripción |
|---|---|---|---|
| `texto` | str | requerido | Texto del anuncio |
| `canales` | list | `["facebook"]` | Canales: `facebook`, `whatsapp`, `telegram` |
| `vacante_id` | str | `""` | UUID de la vacante |
| `empresa_id` | str | `""` | ID de empresa |
| `dry_run` | bool | `true` | Simular sin publicar |
| `whatsapp_destinos` | list | `[]` | Números destino WA (requerido si canal=whatsapp) |
| `telegram_chat_id` | str | `null` | Chat ID (requerido si canal=telegram) |
| `base_dir` | str | `"factory"` | Ruta al directorio factory |

## Salida

```json
{
  "ok": true,
  "data": {
    "exitosos": 2,
    "fallidos": 1,
    "resultados": {
      "facebook": {"ok": true},
      "whatsapp": {"ok": true, "enviados": 3},
      "telegram": {"ok": false, "error": "telegram_chat_id requerido"}
    }
  }
}
```
