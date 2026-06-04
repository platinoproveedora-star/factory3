from service import ErpComprasProductListService


def run(context: dict) -> dict:
    return ErpComprasProductListService().ejecutar(context)
