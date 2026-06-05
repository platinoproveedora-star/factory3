from service import ErpCostingPolicyService


def run(context: dict) -> dict:
    return ErpCostingPolicyService().ejecutar(context)
