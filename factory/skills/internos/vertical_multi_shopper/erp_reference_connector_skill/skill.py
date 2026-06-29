from service import ErpReferenceConnectorSkillService


def run(context: dict) -> dict:
    return ErpReferenceConnectorSkillService().ejecutar(context)
