from service import ErpProjectContextResolveService


def run(context: dict) -> dict:
    return ErpProjectContextResolveService().ejecutar(context)
