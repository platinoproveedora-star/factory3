---
name: vertical_meta_ads/meta_leads_sync_to_sales
vertical: vertical_meta_ads
type: internal
entrypoint: skill.py
contract: run(context) -> dict
---

# meta_leads_sync_to_sales

Sincroniza leads de formularios Meta hacia `vertical_sales/sales_run`, que ya
se encarga de router, dedup, pipeline, score y follow-up.
