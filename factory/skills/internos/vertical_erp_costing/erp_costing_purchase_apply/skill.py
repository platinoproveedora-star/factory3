from service import ErpCostingPurchaseApplyService


def run(context: dict) -> dict:
    return ErpCostingPurchaseApplyService().ejecutar(context)
