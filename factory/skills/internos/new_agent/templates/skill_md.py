def render(
    nombre: str,
    agent_id: str,
    vertical: str,
    descripcion: str,
    mcps: list[str],
    skills: list[str],
) -> str:
    deps = mcps + skills
    deps_str = "\n".join(f"  - {dep}" for dep in deps) or "  []"
    return f"""---
name: {nombre}
agent_id: {agent_id}
description: {descripcion}
version: "0.1.0"
vertical: {vertical}
type: agent
dependencies:
{deps_str}
---

## Rol

{descripcion}

## Responsabilidades

TODO: definir responsabilidades.

## Cuando activarme

TODO: definir triggers.
"""
