from service import MultiShopperActivityLogSkillService


def run(context: dict) -> dict:
    return MultiShopperActivityLogSkillService().ejecutar(context)
