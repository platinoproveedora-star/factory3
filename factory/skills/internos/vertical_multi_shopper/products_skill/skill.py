from service import ProductsSkillService


def run(context: dict) -> dict:
    return ProductsSkillService().ejecutar(context)
