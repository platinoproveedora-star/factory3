# context_loader

Carga el contexto completo del proyecto Factory al inicio de un nuevo chat: registries de skills, bots y agentes, y todos los archivos Markdown de raíz y docs/.

## Entradas

| campo             | tipo   | default    | descripción                                       |
|-------------------|--------|------------|---------------------------------------------------|
| `base_dir`        | str    | `"factory"`| Ruta relativa al directorio factory               |
| `include_docs`    | bool   | `true`     | Leer .md de raíz y docs/                         |
| `include_skills`  | bool   | `true`     | Incluir factory/skills/registry.json             |
| `include_bots`    | bool   | `true`     | Incluir factory/bots/registry.json               |
| `include_agents`  | bool   | `true`     | Incluir factory/agents/registry.json             |
| `include_mcp`     | bool   | `false`    | Incluir factory/mcp/registry.json                |
| `include_skill_docs` | bool | `false`  | Leer SKILL.md de cada skill del registry         |

## Salida

```json
{
  "ok": true,
  "data": {
    "docs": {
      "README.md": "...",
      "SESION_ACTUAL.md": "...",
      "docs/VERTICAL_RH.md": "..."
    },
    "skills": { "nombre_skill": { "descripcion": "...", "vertical": "..." } },
    "bots": { ... },
    "agents": { ... }
  }
}
```

## Uso típico

Primer skill a correr en un chat nuevo para cargar todo el contexto:

```python
result = run({})
```
