# meta_get_instagram_account

Obtiene la cuenta de Instagram Business conectada a una Page con
`/{version}/{page_id}?fields=instagram_business_account{id,username,name,profile_picture_url}`.

## Input

- `page_id` (requerido): ID de la Page de Meta/Facebook.
- `access_token` (opcional): page token o token con acceso a la Page.
- `dry_run` (opcional): si es `true`, devuelve el request planeado sin llamar a Meta ni requerir token real.

Si `access_token` no viene en context, usa `META_ACCESS_TOKEN` o `IG_ACCESS_TOKEN`.
La version se lee desde `META_GRAPH_API_VERSION` y por defecto es `v24.0`.

## Output

Devuelve `{"ok": true, "data": {"page_id": "...", "instagram_business_account": {...}}}`
o `{"ok": false, "error": "..."}`.
