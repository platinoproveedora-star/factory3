from service import ErpInventoryLotStockReportService


def run(context: dict) -> dict:
    return ErpInventoryLotStockReportService().ejecutar(context)
