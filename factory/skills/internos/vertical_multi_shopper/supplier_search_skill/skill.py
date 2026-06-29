from service import SupplierSearchSkillService


def run(context: dict) -> dict:
    return SupplierSearchSkillService().ejecutar(context)
