from service import MultiShopperSchemaPlanService


def run(context: dict) -> dict:
    return MultiShopperSchemaPlanService().ejecutar(context)
