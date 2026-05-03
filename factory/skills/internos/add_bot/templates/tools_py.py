def render(commands: list[str]) -> str:
    responses = {cmd: f"Comando /{cmd} recibido." for cmd in commands}
    responses["message"] = "Mensaje recibido. Aun no tengo cerebro conectado."
    lines = "\n".join(f'    "{k}": "{v}",' for k, v in responses.items())
    return f'''"""Basic configurable bot tool."""


RESPONSES = {{
{lines}
}}


def responder_comando(command: str, text: str) -> str:
    return RESPONSES.get(command, RESPONSES["message"])
'''
