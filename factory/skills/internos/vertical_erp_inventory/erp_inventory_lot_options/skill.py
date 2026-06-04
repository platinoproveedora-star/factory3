from service import ErpInventoryLotOptionsService


def run(context: dict) -> dict:
    return ErpInventoryLotOptionsService().ejecutar(context)
