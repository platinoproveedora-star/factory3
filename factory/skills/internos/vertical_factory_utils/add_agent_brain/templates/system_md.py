def render(agent_name: str, system_prompt: str) -> str:
    return f"""# System Prompt: {agent_name}

{system_prompt.strip()}
"""
