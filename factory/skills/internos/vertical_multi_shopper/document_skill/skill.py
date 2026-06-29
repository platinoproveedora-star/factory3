from service import DocumentSkillService


def run(context: dict) -> dict:
    return DocumentSkillService().ejecutar(context)
