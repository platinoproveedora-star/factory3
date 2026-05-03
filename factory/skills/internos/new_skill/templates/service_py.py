def render(class_name: str) -> str:
    return f'''"""Service for this skill."""


class {class_name}Service:

    def ejecutar(self, context: dict) -> dict:
        return {{
            "ok": True,
            "message": "skill ejecutado; logica pendiente",
            "data": {{"received_context": context}},
        }}
'''
