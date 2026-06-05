from service import ErpCostingWeightedAverageRebuildService


def run(context: dict) -> dict:
    return ErpCostingWeightedAverageRebuildService().ejecutar(context)
