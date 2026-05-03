# vertical_meta

Conecta y valida cuentas Meta para que otras verticales, especialmente
`vertical_instagram`, puedan operar con tokens, paginas y cuentas profesionales.

## Objetivo

Separar autenticacion, permisos y descubrimiento de assets Meta de los skills
especificos de Instagram. Meta conecta; Instagram publica, analiza y responde.

## Skills core

### OAuth y tokens
- `meta_get_auth_url` - genera URL OAuth con scopes requeridos.
- `meta_exchange_code` - intercambia `code` OAuth por access token.
- `meta_extend_token` - convierte token corto en long-lived token.

### Descubrimiento y permisos
- `meta_debug_token` - valida token, expiracion, scopes y app.
- `meta_get_permissions` - lista permisos concedidos/declinados.
- `meta_list_pages` - lista paginas administradas por el usuario.
- `meta_get_instagram_account` - obtiene la cuenta profesional IG conectada a una pagina.

### Conexion
- `meta_connection_check` - revisa si una conexion puede publicar, leer insights y responder.
- `meta_refresh_connection` - reconsulta estado de token, pagina y cuenta IG.
- `meta_store_connection` - normaliza payload portable para persistir.
- `meta_revoke_connection` - revoca permisos del token.

## Variables de entorno

```
META_APP_ID=
META_APP_SECRET=
META_REDIRECT_URI=
META_ACCESS_TOKEN=
META_PAGE_ID=
META_IG_USER_ID=
META_GRAPH_API_VERSION=v24.0
```

`IG_ACCESS_TOKEN` e `IG_BUSINESS_ACCOUNT_ID` pueden seguir existiendo como fallback
para skills `ig_*`, pero la ruta recomendada es pasar un objeto `connection`
normalizado desde `vertical_meta`.
