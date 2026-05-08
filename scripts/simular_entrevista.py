"""Corre rh_interview_simulator localmente contra la vacante VAC-001."""
import os, sys
from pathlib import Path

for line in (Path(__file__).parent.parent / ".env").read_text(encoding="utf-8").splitlines():
    raw = line.strip()
    if not raw or raw.startswith("#") or "=" not in raw:
        continue
    k, v = raw.split("=", 1)
    k = k.strip(); v = v.strip().strip('"').strip("'")
    if k and k not in os.environ:
        os.environ[k] = v

os.environ["FACTORY_API_URL"] = "http://localhost:8000"

sys.path.insert(0, str(Path(__file__).parent.parent))
from factory.engine import SkillLoader, SkillRunner

base   = Path(__file__).parent.parent
ext    = base / "factory" / "skills" / "externos"
ext.mkdir(parents=True, exist_ok=True)
loader = SkillLoader(internal_root=base / "factory" / "skills" / "internos", external_root=ext)
runner = SkillRunner(loader)

result = runner.run("rh_interview_simulator", {
    "vacante_id":     "6030dbc2-9de2-47b0-b5e9-22879574ce17",  # VAC-001
    "delay_seconds":  2,
    "dry_run":        False,
}, source="internos")

import json
print(json.dumps(result, indent=2, ensure_ascii=False))
