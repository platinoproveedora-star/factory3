# rh_qr_entry

Genera un link directo al bot de captura para una vacante, con QR opcional si `qrcode` está instalado.

## Entradas

| campo | tipo | default | descripción |
|---|---|---|---|
| `bot_url` | str | requerido | URL base del bot (ej: `https://t.me/mi_bot`) |
| `vacante_id` | str | `""` | UUID de la vacante |
| `empresa_id` | str | `""` | ID de empresa |
| `canal` | str | `"telegram"` | Canal destino |

## Salida

```json
{
  "ok": true,
  "data": {
    "link": "https://t.me/mi_bot?vacante_id=abc&empresa_id=xyz",
    "qr_generado": true,
    "qr_b64": "iVBORw0KGgo..."
  }
}
```

## Nota
Si `qrcode` no está instalado, devuelve solo el link sin QR.
