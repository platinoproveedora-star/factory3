# meta_debug_token

Inspecciona un token de Meta Graph API usando `/{version}/debug_token`.

## Input

- `input_token` (requerido): token que se quiere inspeccionar.
- `app_access_token` (opcional): token de app para autorizar `debug_token`.
- `app_id` y `app_secret` (opcional): alternativa para construir `app_id|app_secret`.
- `dry_run` (opcional): si es `true`, devuelve el request planeado sin llamar a Meta ni requerir token de app real.

Tambien acepta `META_APP_ID`, `META_APP_SECRET` y `META_GRAPH_API_VERSION`.
La version por defecto es `v24.0`.

## Output

Devuelve `{"ok": true, "data": {...}}` con el objeto `data` de Meta, o
`{"ok": false, "error": "..."}` si falla la validacion o la API.
