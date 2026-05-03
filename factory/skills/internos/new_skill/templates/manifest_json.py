import json


def render(nombre: str, vertical: str, descripcion: str) -> str:
    return json.dumps(
        {
            "type": "skill",
            "name": nombre,
            "version": "0.1.0",
            "kind": "executable",
            "entrypoint": "skill.py",
            "description": descripcion,
            "vertical": vertical,
            "permissions": [],
            "requires_env": [],
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n"
