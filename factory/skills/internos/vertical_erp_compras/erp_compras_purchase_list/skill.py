from service import ErpComprasPurchaseListService


def run(context: dict) -> dict:
    return ErpComprasPurchaseListService().ejecutar(context)
