# vertical_vercel — Publicar y operar proyectos en Vercel

## Objetivo
Crear, configurar, deployar y operar proyectos en Vercel desde factory3.
Diseñada para publicar dashboards Next.js generados por `vertical_dashboards`.

## Env vars requeridas

| Variable | Obligatoria | Descripción |
|---|---|---|
| `VERCEL_TOKEN` | ✅ | Token de API — vercel.com/account/tokens |
| `VERCEL_TEAM_ID` | ❌ | Solo si usas Vercel Teams (empieza con `team_`) |

## Skills

### vercel_project_list
Lista todos los proyectos de la cuenta con su URL de producción y estado.
```python
run("vercel_project_create", {
    "limit": 20,           # opcional, default 20
    "search": "duralon",   # opcional, filtro por nombre
})
# → {"ok": True, "data": {"projects": [{name, url, state, last_deploy}]}}
```

### vercel_project_get
Detalle de un proyecto: repo vinculado, envs visibles, últimos deploys.
```python
run("vercel_project_get", {
    "name": "duralon-dash",   # nombre del proyecto en Vercel
})
# → {"ok": True, "data": {"project": {...}, "deployments": [...]}}
```

### vercel_project_create
Crea un proyecto nuevo en Vercel conectado a un repo GitHub.
```python
run("vercel_project_create", {
    "name":       "duralon-dash",         # nombre del proyecto
    "repo":       "org/repo-name",        # GitHub full_name
    "framework":  "nextjs",               # nextjs | other
    "root_dir":   "",                     # "" = raíz del repo
})
# → {"ok": True, "data": {"project_id": "...", "url": "...", "name": "..."}}
```

### vercel_env_sync
Configura variables de entorno en un proyecto (crea o sobreescribe).
```python
run("vercel_env_sync", {
    "project_id": "prj_xxx",
    "envs": {
        "SUPABASE_URL": "https://...",
        "SUPABASE_SERVICE_ROLE_KEY": "...",
        "NEXT_PUBLIC_API_URL": "https://factory3.onrender.com",
    },
    "target": ["production", "preview"],  # opcional, default ambos
})
# → {"ok": True, "data": {"synced": 3, "vars": ["SUPABASE_URL", ...]}}
```

### vercel_deploy_trigger
Dispara un deploy de production o preview.
```python
run("vercel_deploy_trigger", {
    "project_id": "prj_xxx",
    "target":     "production",   # production | preview
})
# → {"ok": True, "data": {"deployment_id": "dpl_xxx", "state": "BUILDING"}}
```

### vercel_deploy_status
Consulta el estado de un deploy hasta que llega a READY o ERROR.
```python
run("vercel_deploy_status", {
    "deployment_id": "dpl_xxx",
    "wait":          True,    # espera hasta READY/ERROR (max 3 min)
})
# → {"ok": True, "data": {"state": "READY", "url": "https://...", "elapsed_s": 42}}
```

### vercel_domain_setup
Conecta un dominio o subdominio a un proyecto.
```python
run("vercel_domain_setup", {
    "project_id": "prj_xxx",
    "domain":     "dash.duralon.mx",
})
# → {"ok": True, "data": {"domain": "dash.duralon.mx", "dns": {...}}}
```

### vercel_rollback
Regresa el proyecto al deploy anterior (o a un deployment_id específico).
```python
run("vercel_rollback", {
    "project_id":    "prj_xxx",
    "deployment_id": "dpl_yyy",  # opcional — si no, usa el penúltimo deploy
})
# → {"ok": True, "data": {"rolled_back_to": "dpl_yyy", "url": "..."}}
```

### vercel_project_remove
Elimina un proyecto y todos sus deployments. Requiere confirm: true.
```python
run("vercel_project_remove", {
    "project_id": "prj_xxx",
    "confirm":    True,
})
# → {"ok": True, "data": {"removed": "duralon-dash"}}
```

## Flujo completo — nuevo dashboard

```
1. vercel_project_create  → project_id
2. vercel_env_sync        → vars configuradas
3. vercel_deploy_trigger  → deployment_id
4. vercel_deploy_status   → URL lista
5. vercel_domain_setup    → dominio propio (opcional)
```

## Flujo — rollback de emergencia

```
1. vercel_project_get     → ver lista de deploys recientes
2. vercel_rollback        → volver al deploy anterior
3. vercel_deploy_status   → confirmar que está READY
```

## Base URL de la API
```
https://api.vercel.com
Authorization: Bearer {VERCEL_TOKEN}
```

## Notas de arquitectura
- `VERCEL_TEAM_ID` se pasa como query param `?teamId=team_xxx` en cada request
- Los proyectos se crean sin repo si no tienes GitHub conectado (deploy via API)
- `vercel_deploy_trigger` usa el último commit del repo vinculado
- Para deployar archivos directamente (sin repo) usar `vercel_deploy_trigger` con `files: {...}`
