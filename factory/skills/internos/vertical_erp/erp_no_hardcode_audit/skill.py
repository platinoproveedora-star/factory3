from service import ErpNoHardcodeAuditService


def run(context: dict) -> dict:
    return ErpNoHardcodeAuditService().ejecutar(context)
