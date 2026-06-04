from service import ErpComprasPurchaseCreateService


def run(context: dict) -> dict:
    return ErpComprasPurchaseCreateService().ejecutar(context)
