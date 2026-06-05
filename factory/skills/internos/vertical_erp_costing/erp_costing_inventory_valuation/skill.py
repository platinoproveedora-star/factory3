from service import ErpCostingInventoryValuationService


def run(context: dict) -> dict:
    return ErpCostingInventoryValuationService().ejecutar(context)
