# meta_get_permissions

Lista permisos del token actual usando `/{version}/me/permissions`.

## Input

- `access_token` (opcional): token de usuario o sistema.
- `dry_run` (opcional): si es `true`, devuelve el request planeado sin llamar a Meta ni requerir token real.

Si `access_token` no viene en context, usa `META_ACCESS_TOKEN` o `IG_ACCESS_TOKEN`.
La version se lee desde `META_GRAPH_API_VERSION` y por defecto es `v24.0`.

## Output

Devuelve `{"ok": true, "data": {"permissions": [...], "paging": ...}}` o
`{"ok": false, "error": "..."}`.
