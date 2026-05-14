---
name: vertical_companies/company_dashboard_scaffold
vertical: vertical_companies
type: internal
entrypoint: skill.py
contract: run(context) -> dict
---

# company_dashboard_scaffold

Crea un dashboard Streamlit base para una empresa nueva con `Campaign Ops`
integrado. Complementa a `new_dashboard`: este skill no usa IA y esta enfocado
en dashboards de empresas configuradas en `companies/<COMPANY_ID>`.

## Estilo default

Genera dashboards con tema claro profesional: fondos claros, tarjetas solidas,
bordes visibles, texto oscuro e inputs nativos legibles. No debe usar reglas CSS
globales sobre todos los `div` o `span`, porque eso rompe campos de texto,
selects y file upload de Streamlit.
