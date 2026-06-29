from service import SalesQuoteItemsSkillService


def run(context: dict) -> dict:
    return SalesQuoteItemsSkillService().ejecutar(context)
