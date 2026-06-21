from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from bank_statement_profile_learn.service import BankStatementProfileLearnService

def run(context: dict) -> dict:
    if not isinstance(context, dict):
        return {"ok": False, "error": "context debe ser dict"}
    return BankStatementProfileLearnService().ejecutar(context)
