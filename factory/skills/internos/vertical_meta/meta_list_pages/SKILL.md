# meta_list_pages

Lista paginas disponibles para el token con `/{version}/me/accounts`.

## Input

- `access_token` (opcional): token con permisos para listar paginas.
- `limit` (opcional): limite de resultados enviado a Graph API.
- `dry_run` (opcional): si es `true`, devuelve el request planeado sin llamar a Meta ni requerir token real.

Si `access_token` no viene en context, usa `META_ACCESS_TOKEN` o `IG_ACCESS_TOKEN`.
La version se lee desde `META_GRAPH_API_VERSION` y por defecto es `v24.0`.

## Output

Devuelve `{"ok": true, "data": {"pages": [...], "paging": ...}}`.
Cada pagina solicita `id,name,access_token,instagram_business_account`.
