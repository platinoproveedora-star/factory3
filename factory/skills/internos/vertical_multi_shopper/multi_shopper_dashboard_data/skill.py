from service import MultiShopperDashboardDataSkillService


def run(context: dict) -> dict:
    return MultiShopperDashboardDataSkillService().ejecutar(context)
