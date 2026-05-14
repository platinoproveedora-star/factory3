---
name: vertical_companies/company_config_loader
vertical: vertical_companies
type: internal
entrypoint: skill.py
contract: run(context) -> dict
---

# company_config_loader

Carga `companies/<COMPANY_ID>/company.config.json` y devuelve la configuracion
normalizada. Acepta `company_id` o `config_path`.
