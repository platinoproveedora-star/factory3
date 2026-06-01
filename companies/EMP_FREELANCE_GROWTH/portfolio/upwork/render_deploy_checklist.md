# Render Deploy Checklist — Cuenta Nueva

## Pasos de tu parte

1. Abrir incógnito → render.com → Sign Up con Gmail nuevo
2. Dashboard → Account → API Keys → New API Key → copiar key
3. Pegar key al chat → yo configuro todo desde aquí

---

## Servicios a crear (yo los creo con la API key)

### Servicio 1: factory3 (API principal)
- Repo: `platinoproveedora-star/factory3`, rama `main`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn factory_api:app --host 0.0.0.0 --port $PORT`
- Plan: Starter ($7/mes) — Free duerme y los webhooks fallan
- Env vars necesarias (19):

```
ANTHROPIC_API_KEY
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
SUPABASE_ANON_KEY
SUPABASE_PROJECT_REF
SUPABASE_ACCESS_TOKEN
GITHUB_TOKEN
RENDER_API_KEY
RENDER_OWNER_ID
FACTORY3_ADMIN_BOT_TOKEN
META_APP_ID
META_APP_SECRET
META_REDIRECT_URI
META_ACCESS_TOKEN
META_PAGE_ID
META_IG_USER_ID
META_GRAPH_API_VERSION=v24.0
IG_ACCESS_TOKEN
IG_BUSINESS_ACCOUNT_ID
```

### Servicio 2: uc101-proy001 (Duralon dashboard)
- Repo: `platinoproveedora-star/uc101-proy001`, rama `main`
- Build: `pip install -r requirements.txt`
- Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
- Plan: Free (dashboard, no necesita estar siempre activo)
- Env vars (solo 2):
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`

---

## Después del deploy (yo lo hago)

- Actualizar webhooks Telegram con la nueva URL de factory3
- Verificar `GET /health` responde 200
- Verificar `GET /data/vertical_client_expenses/client_expenses_dashboard_data?action=stats&client_id=UC-101&project_code=PROY-001`

---

## Orden de prioridad
1. factory3 primero — los bots dependen de él
2. uc101-proy001 después — solo para screenshots y cliente
