from service import ErpComprasSupplierListService


def run(context: dict) -> dict:
    return ErpComprasSupplierListService().ejecutar(context)
