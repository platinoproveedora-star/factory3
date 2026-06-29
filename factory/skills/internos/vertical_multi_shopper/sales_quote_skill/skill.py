from service import SalesQuoteSkillService


def run(context: dict) -> dict:
    return SalesQuoteSkillService().ejecutar(context)
