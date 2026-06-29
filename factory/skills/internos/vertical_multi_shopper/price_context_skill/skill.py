from service import PriceContextSkillService


def run(context: dict) -> dict:
    return PriceContextSkillService().ejecutar(context)
