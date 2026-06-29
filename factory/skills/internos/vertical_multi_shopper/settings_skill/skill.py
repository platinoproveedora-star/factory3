from service import SettingsSkillService


def run(context: dict) -> dict:
    return SettingsSkillService().ejecutar(context)
