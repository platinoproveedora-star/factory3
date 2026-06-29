from service import PurchaseQuoteResponseIngestionSkillService


def run(context: dict) -> dict:
    return PurchaseQuoteResponseIngestionSkillService().ejecutar(context)
