from service import SupplierCategorySkillService


def run(context: dict) -> dict:
    return SupplierCategorySkillService().ejecutar(context)
