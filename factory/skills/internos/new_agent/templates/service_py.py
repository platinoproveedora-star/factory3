import json


def render(nombre: str, agent_id: str, descripcion: str, mcps: list[str], skills: list[str]) -> str:
    nombre_json = json.dumps(nombre, ensure_ascii=False)
    agent_id_json = json.dumps(agent_id, ensure_ascii=False)
    descripcion_json = json.dumps(descripcion, ensure_ascii=False)
    mcps_json = json.dumps(mcps, ensure_ascii=False)
    skills_json = json.dumps(skills, ensure_ascii=False)
    return f'''"""Service for agent {nombre}."""


class AgentService:

    def ejecutar(self, context: dict) -> dict:
        return {{
            "ok": True,
            "message": "agente generado; logica pendiente",
            "data": {{
                "agent": {nombre_json},
                "agent_id": {agent_id_json},
                "descripcion": {descripcion_json},
                "mcps": {mcps_json},
                "skills": {skills_json},
                "received_context": context,
            }},
        }}
'''
