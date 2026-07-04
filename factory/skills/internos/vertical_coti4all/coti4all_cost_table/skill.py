from __future__ import annotations
import importlib.util
from pathlib import Path


def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    _p = Path(__file__).parent / "service.py"
    _spec = importlib.util.spec_from_file_location("coti4all_cost_table_svc", _p)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod.Coti4AllCostTableService().ejecutar(context)
