---
name: meta_revoke_connection
vertical: vertical_meta
kind: executable
entrypoint: skill.py
requires_env: []
---

# meta_revoke_connection

Revoca permisos de una conexion Meta con `DELETE /me/permissions`.

## Input

- `access_token` requerido, o `META_ACCESS_TOKEN` / `IG_ACCESS_TOKEN`.
- `graph_version` opcional. Default `META_GRAPH_API_VERSION`, `IG_GRAPH_API_VERSION` o `v24.0`.
- `dry_run` opcional.

## Output

Devuelve la respuesta de Graph API, normalmente `{"success": true}`.
