from service import ErpInventoryKardexLotReassignService


def run(context: dict) -> dict:
    return ErpInventoryKardexLotReassignService().ejecutar(context)
