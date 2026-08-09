from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from service import LogisticsPurchaseOrderManageService  # noqa: E402


def run(context: dict) -> dict:
    return LogisticsPurchaseOrderManageService().ejecutar(context)
