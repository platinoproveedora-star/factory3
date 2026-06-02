# EMP_DURALON

**COMERCIALIZADORA DURALON DE CHIAPAS SA DE CV**

Empresa con varios modulos operativos en construccion. Identidad principal: `EMP_DURALON`. Legacy alias: `UC-101`.

## Proyectos

| Codigo | Modulo | Estado | Dashboard |
|---|---|---|---|
| PROY-001 | gastos | ERP-ready / in_progress | https://uc101-gastos.onrender.com |
| PROY-002 | ventas | planned / pausado | - |
| PROY-003 | erp_core | planned | - |
| PROY-004 | inventario | in_progress | - |

## Infraestructura

| Recurso | Valor |
|---|---|
| Bot Telegram | @Duralon1_bot |
| Schema gastos | `uc101_proy001` |
| Schema ventas previsto | `uc101_proy002` |
| Schema inventario previsto | `uc101_proy004` |
| Bucket Storage | `uc101-proy001-assets` |
| Repo dashboard gastos | `platinoproveedora-star/uc101-proy001` |
| Factory API | https://factory3.onrender.com |

## Identidad ERP

```text
empresa_id = EMP_DURALON
company_id = EMP_DURALON
legacy_id = UC-101
PROY-001 = gastos
PROY-002 = ventas
PROY-003 = erp_core
PROY-004 = inventario
```

Todo registro operativo lleva: `empresa_id` + `project_code` + `module_code` + `id uuid` + `folio text unique`.

## ERP Core

La arquitectura movible del ERP vive dentro del proyecto:

```text
companies/EMP_DURALON/projects/PROY-003_ERP_CORE/
```

No mantener documentos de arquitectura ERP en la raiz de `EMP_DURALON`; deben ir dentro de `PROY-003_ERP_CORE` para que el ERP completo pueda moverse como paquete.

## Archivos clave

```text
companies/EMP_DURALON/
  README.md
  company.json
  projects/
    PROY-001_GASTOS/
      dashboard/gastos/
    PROY-002_VENTAS/
    PROY-003_ERP_CORE/
    PROY-004_INVENTARIO/

factory/skills/internos/
  vertical_client_expenses/
  vertical_erp/
  vertical_erp_inventory/
```
