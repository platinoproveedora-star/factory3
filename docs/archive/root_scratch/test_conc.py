import os, json
from pathlib import Path

# Cargar .env
for line in (Path(__file__).parent / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import sys; sys.path.insert(0, str(Path(__file__).parent))
from factory.skills.internos.vertical_erp_billing.erp_billing_conciliacion_data.service import ErpBillingConciliacionDataService

ctx = {
    "company_id": "EMP_DURALON",
    "schema": "uc101_proy005",
    "sales_schema": "uc101_proy002",
    "banks_schema": "uc101_banks",
    "project_code": "PROY-005",
    "module_code": "billing",
}

r = ErpBillingConciliacionDataService().ejecutar(ctx)
if not r.get("ok"):
    print("ERROR:", r.get("error"))
else:
    d = r["data"]
    print("STATS:", json.dumps(d["stats"], indent=2))
    print("\n--- matched (primeros 3) ---")
    for x in d["matched"][:3]:
        print(f"  {x.get('folio')} | {x.get('movement_date')} | ${x.get('amount')} | -> {x.get('payment', {}).get('folio')} | {x.get('match_type')}")
    print("\n--- solo_banco (primeros 3) ---")
    for x in d["solo_banco"][:3]:
        print(f"  {x.get('folio')} | {x.get('movement_date')} | ${x.get('amount')} | rastreo: {x.get('clave_rastreo')}")
    print("\n--- solo_billing (primeros 3) ---")
    for x in d["solo_billing"][:3]:
        print(f"  {x.get('folio')} | {x.get('payment_date')} | ${x.get('amount')} | {x.get('customer_name')} | {x.get('confirmation_status')}")
