# Notes - PROY-003_ERP_CORE

## Decision

La arquitectura movible del ERP vive dentro de `PROY-003_ERP_CORE`, no suelta en la raiz de `EMP_DURALON`.

La raiz de la empresa puede tener un indice o resumen, pero el paquete portable del ERP debe ser este proyecto.

## Contexto

`PROY-001_GASTOS` nacio con alias legacy `UC-101`, pero ya fue normalizado con identidad principal `EMP_DURALON`.

`PROY-002_VENTAS` debe nacer con contrato `vertical_erp` desde el inicio.

