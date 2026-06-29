from service import SupplierRegistrySkillService


def run(context: dict) -> dict:
    return SupplierRegistrySkillService().ejecutar(context)
