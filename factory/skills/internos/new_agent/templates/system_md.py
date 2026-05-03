def render(nombre: str, descripcion: str) -> str:
    return f"# System Prompt: {nombre}\n\n{descripcion.strip()}\n"
