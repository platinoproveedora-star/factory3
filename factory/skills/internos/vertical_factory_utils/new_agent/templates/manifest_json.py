import json


def render(
    nombre: str,
    agent_id: str,
    vertical: str,
    descripcion: str,
    mcps: list[str],
    skills: list[str],
    memory: dict | None = None,
) -> str:
    manifest = {
        "type": "agent",
        "name": nombre,
        "agent_id": agent_id,
        "version": "0.1.0",
        "kind": "executable",
        "entrypoint": "agent.py",
        "description": descripcion,
        "vertical": vertical,
        "mcps": mcps,
        "skills": skills,
        "permissions": [],
        "requires_env": ["ANTHROPIC_API_KEY"],
        "brain": {
            "provider": "anthropic",
            "model": "claude-3-5-haiku-latest",
            "entrypoint": "agent_brain.py",
            "system_prompt": "prompts/system.md",
        },
    }
    if memory:
        manifest["memory"] = memory
    return json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False,
    ) + "\n"
