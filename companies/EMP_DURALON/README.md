# EMP_DURALON

**COMERCIALIZADORA DURALON DE CHIAPAS SA DE CV**

Empresa con varios módulos operativos en construcción. Identidad principal: `EMP_DURALON`. Legacy alias: `UC-101`.

## Proyectos

| Código | Módulo | Estado | Dashboard |
|---|---|---|---|
| PROY-001 | gastos | in_progress | https://uc101-gastos.onrender.com |
| PROY-002 | ventas | pendiente | — |

## Infraestructura

| Recurso | Valor |
|---|---|
| Bot Telegram | @Duralon1_bot |
| Schema Supabase | `uc101_proy001` |
| Bucket Storage | `uc101-proy001-assets` |
| Repo dashboard | `platinoproveedora-star/uc101-proy001` |
| Factory API | https://factory3.onrender.com |

## Identidad ERP

```
empresa_id   = EMP_DURALON
company_id   = EMP_DURALON
legacy_id    = UC-101
PROY-001     = gastos
PROY-002     = ventas
```

Todo registro operativo lleva: `empresa_id` + `project_code` + `module_code` + `id uuid` + `folio text unique`.

## Archivos clave

```
companies/EMP_DURALON/
├── README.md                          ← este archivo
├── company.json                       ← datos empresa
├── ERP_ARCHITECTURE.md                ← arquitectura ERP multi-módulo
└── projects/
    ├── PROY-001_GASTOS/               ← bot + dashboard gastos
    └── PROY-002_VENTAS/               ← (próximo)

EMP_DURALON/dashboards/
└── gastos/                            ← Next.js dashboard deployado en Render

factory/bots/duralon1_bot/             ← bot Telegram
factory/skills/internos/
└── vertical_client_expenses/          ← CRUD gastos + dashboard data API
```
