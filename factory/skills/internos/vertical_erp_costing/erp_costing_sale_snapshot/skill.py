from service import ErpCostingSaleSnapshotService


def run(context: dict) -> dict:
    return ErpCostingSaleSnapshotService().ejecutar(context)
