# Factory3 MCP Bridge

Puente MCP delgado entre Hermes y los skills de Factory3. No duplica logica:
lee `factory/skills/registry.json` para descubrimiento y ejecuta skills via el
endpoint existente `POST /run/{skill_name}` de `factory_api.py`.

## Setup

```bash
pip install -r requirements.txt
```

Variables de entorno:

| Variable | Uso |
|---|---|
| `FACTORY_API_URL` | URL del Factory API desplegado en Render. |
| `FACTORY_RUN_SECRET` | Mismo secreto configurado en el servicio Render de Factory API. |
| `REGISTRY_PATH` | Opcional. Ruta local a `factory/skills/registry.json`. |

Si `REGISTRY_PATH` se omite, el servidor intenta usar
`../skills/registry.json` relativo a `factory/mcp/server.py`. Si no existe,
hace fallback al registry crudo en GitHub.

## Seguridad

Antes de conectar Hermes en produccion, `FACTORY_RUN_SECRET` debe existir en el
servicio Render que corre `factory_api.py`. El endpoint `/run/` de Factory API
solo exige Bearer token cuando esa variable existe.

Generar un secreto:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

No pegues ese valor en chats, docs ni commits. Debe configurarse en Render y en
el entorno donde corra Hermes/MCP.

## Hermes con stdio

Para el piloto inicial, correrlo en el VPS de Hermes con transporte `stdio`:

```bash
hermes mcp add factory3 -- python /ruta/factory3/factory/mcp/server.py
```

## Tools

- `list_verticals()` lista verticales disponibles.
- `list_skills(vertical=None)` lista skills, opcionalmente por vertical.
- `search_skills(query)` busca por nombre o descripcion.
- `get_skill_manifest(skill_name)` devuelve metadata del registry.
- `run_skill(skill_name, context)` ejecuta via Factory API.

## Fase futura

Si varios agentes o clientes necesitan conectarse remotamente, este puente puede
pasar a un servicio chico en Render usando transporte HTTP del SDK MCP.
