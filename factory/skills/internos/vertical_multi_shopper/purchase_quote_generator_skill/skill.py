from service import PurchaseQuoteGeneratorSkillService


def run(context: dict) -> dict:
    return PurchaseQuoteGeneratorSkillService().ejecutar(context)
