from service import VerticalMultiShopperService


def run(context: dict) -> dict:
    return VerticalMultiShopperService().ejecutar(context)
