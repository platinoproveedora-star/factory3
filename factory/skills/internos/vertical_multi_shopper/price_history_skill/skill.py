from service import PriceHistorySkillService


def run(context: dict) -> dict:
    return PriceHistorySkillService().ejecutar(context)
