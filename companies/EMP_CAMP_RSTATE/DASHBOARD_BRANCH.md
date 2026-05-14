# EMP_CAMP_RSTATE Dashboard Branch

## Rama generica sugerida

```text
Campaign Ops
  Overview
  Campaign
  Uploads
  Preflight
  Leads
  Results
  Settings
```

Esta rama debe ser reusable para cualquier empresa de campanas. La plantilla
Streamlit vive en:

```text
factory/dashboard_modules/campaign_ops.py
```

## Para la campana Orion

| Menu | Uso |
| --- | --- |
| `Overview` | Ver si la campana esta lista para lanzar. |
| `Campaign` | Generar dry run y payloads de campana. |
| `Uploads` | Subir fotos/renders de la oficina y obtener `image_url`. |
| `Preflight` | Confirmar blockers antes de crear campana real. |
| `Leads` | Ver leads una vez conectado Supabase sales. |
| `Results` | Ver resultados Meta Ads despues de crear campana. |
| `Settings` | Ver config de `EMP_CAMP_RSTATE`. |

## Render

| Campo | Valor |
| --- | --- |
| Servicio | `emp-camp-rstate-dashboard` |
| URL publica | `https://emp-camp-rstate-dashboard.onrender.com` |
| Render dashboard | `https://dashboard.render.com/web/srv-d830o697oqds739pomo0` |
| Branch | `main` |
| Build command | `pip install -r companies/EMP_CAMP_RSTATE/dashboard/requirements.txt` |
| Start command | `streamlit run companies/EMP_CAMP_RSTATE/dashboard/app.py --server.port=$PORT --server.address=0.0.0.0` |
| Ultimo estado verificado | `live` |

## Datos que faltan para usar Uploads

| Dato | Estado |
| --- | --- |
| Bucket publico de Supabase Storage | Pendiente |
| Fotos de oficina | Pendiente |
| Fotos edificio/lobby | Pendiente |
| WhatsApp/celular destino | Pendiente |
| Privacy URL | Pendiente |

## Integracion en un dashboard existente

Agregar al dashboard:

```python
from factory.dashboard_modules.campaign_ops import render_campaign_ops
```

Y en el menu:

```python
elif page == "Campaign Ops":
    render_campaign_ops(
        run_skill=_run_skill,
        company_id="EMP_CAMP_RSTATE",
        campaign_slug="first_rstate_campaign",
    )
```
